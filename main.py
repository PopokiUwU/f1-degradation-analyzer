import fastf1 as ff1
import os
import matplotlib.pyplot as plt
import numpy as np




def safe_polyfit(group):

    g_clean = group.dropna(subset=['TyreLife', 'CorrTime'])

    if len(g_clean) < 2 or g_clean['TyreLife'].nunique() < 2:
        return np.nan

    slope, intercept = np.polyfit(
        g_clean['TyreLife'],
        g_clean['CorrTime'],
        1
    )

    if slope < 0:
        return np.nan

    return slope


def plot_driver_degradation(df, drivers_to_plot=None):

    plt.figure(figsize=(10, 6))

    # If drivers are not specified, select the first 3 drivers
    if drivers_to_plot is None:
        drivers_to_plot = df['Driver'].unique()[:3]

    for driver in drivers_to_plot:

        driver_df = df[df['Driver'] == driver]

        for stint in driver_df['Stint'].unique():

            stint_data = driver_df[
                driver_df['Stint'] == stint
            ].dropna(subset=['TyreLife', 'CorrTime'])

            if stint_data.empty:
                continue

            compound = (
                stint_data['Compound'].iloc[0]
                if 'Compound' in stint_data.columns
                else 'Unknown'
            )

            # Scatter plot
            plt.scatter(
                stint_data['TyreLife'],
                stint_data['CorrTime'],
                alpha=0.6,
                label=f"{driver} ({compound} - Stint {int(stint)})"
            )

            # Regression - same approach as safe_polyfit()
            if (
                len(stint_data) >= 3
                and stint_data['TyreLife'].nunique() >= 2
            ):

                slope, intercept = np.polyfit(
                    stint_data['TyreLife'],
                    stint_data['CorrTime'],
                    1
                )

                # Reject negative degradation
                if slope >= 0:

                    x = np.linspace(
                        stint_data['TyreLife'].min(),
                        stint_data['TyreLife'].max(),
                        100
                    )

                    p = np.poly1d([slope, intercept])

                    plt.plot(
                        x,
                        p(x),
                        linestyle='--',
                        alpha=0.8
                    )

    plt.title(
        "Tyre Degradation - Drivers",
        fontsize=14,
        fontweight='bold'
    )

    plt.xlabel("Tyre Life [laps]", fontsize=12)
    plt.ylabel("Corrected Lap Time [s]", fontsize=12)

    plt.grid(True, linestyle=':', alpha=0.7)

    plt.legend(
        bbox_to_anchor=(1.05, 1),
        loc='upper left'
    )

    plt.tight_layout()
    plt.show()


def plot_compound_degradation(df):

    plt.figure(figsize=(10, 6))

    compounds = df['Compound'].unique()

    colors = {
        'SOFT': 'red',
        'MEDIUM': 'gold',
        'HARD': 'silver',
        'INTERMEDIATE': 'green',
        'WET': 'blue'
    }

    for compound in compounds:

        comp_data = df[df['Compound'] == compound]

        if comp_data.empty:
            continue

        # Average corrected lap time per stint lap
        grouped = (
            comp_data.groupby('StintLap')['CorrTime']
            .mean()
            .reset_index()
        )

        color = colors.get(compound, 'black')

        plt.plot(
            grouped['StintLap'],
            grouped['CorrTime'],
            marker='o',
            linewidth=2,
            label=f"Compound: {compound}",
            color=color
        )

    plt.title(
        "Comparison of Tyre Compound Degradation",
        fontsize=14,
        fontweight='bold'
    )

    plt.xlabel("Stint Lap", fontsize=12)
    plt.ylabel("Corrected Average Lap Time [s]", fontsize=12)

    plt.grid(True, linestyle=':', alpha=0.7)
    plt.legend(fontsize=12)

    plt.tight_layout()
    plt.show()



os.makedirs('cache', exist_ok=True)

ff1.Cache.configure(cache_dir='cache')

email = input("Enter your email here ")
password = input("Enter your password here ")

os.environ['F1_USERNAME'] = email
os.environ['F1_PASSWORD'] = password



year = int(input("Give year of the GP "))

round_identifier = input(
    "Give the name of the track (e.g. 'Monza') "
    "or the round number (e.g. 20)"
)

if round_identifier.isdigit():
    round_identifier = int(round_identifier)

session = ff1.get_session(year, round_identifier, 'R')
session.load()

laps = session.laps



laps['LapSecondTime'] = laps['LapTime'].dt.total_seconds()

conditions = [
    laps['TrackStatus'].str.contains('5'),
    laps['TrackStatus'].str.contains('4|6|7')
]

values = [0.1, 0.6]

laps['FuelUsage'] = np.select(
    conditions,
    values,
    default=1.65
)

laps['UsedFuel'] = (
    laps.groupby(['Driver'])['FuelUsage'].cumsum()
    - laps['FuelUsage']
)

laps['UsedFuel'] = laps['UsedFuel'].fillna(0)


# Predicted fuel consumption
laps['PredFuelUsageOnLap'] = 1.65

laps['PredUsedFuel'] = (
    laps.groupby(['Driver'])['PredFuelUsageOnLap'].cumsum()
    - laps['PredFuelUsageOnLap']
)

FuelWeight = laps['PredUsedFuel'].max() + 1.75  # Safety reserve

mass_sensitivity = 0.032

laps['CorrTime'] = (
    laps['LapSecondTime']
    - mass_sensitivity * (FuelWeight - laps['UsedFuel'])
)



laps['MedianTime'] = (
    laps.groupby('LapNumber')['CorrTime']
    .transform('median')
)

base_median = np.nan

for lap_num in sorted(laps['LapNumber'].unique()):

    subset = laps.loc[
        laps['LapNumber'] == lap_num,
        'MedianTime'
    ]

    if not subset.dropna().empty:
        base_median = subset.dropna().iloc[0]
        break

laps['CorrTime'] = (
    laps['CorrTime']
    + (base_median - laps['MedianTime'])
)



cleanlaps = laps[
    (laps['PitInTime'].isnull()) &
    (laps['PitOutTime'].isnull()) &
    (~laps['TrackStatus'].str.contains('4|5|6|7')) &
    (laps['LapNumber'] > 1) &
    (laps['Compound'].str.contains('SOFT|MEDIUM|HARD'))
][[
    'LapNumber',
    'PitInTime',
    'Driver',
    'Compound',
    'TyreLife',
    'TrackStatus',
    'CorrTime',
    'Stint'
]]



cleanlaps['DiffPrev'] = (
    cleanlaps['CorrTime']
    - cleanlaps.groupby(['Driver', 'Stint'])['CorrTime'].shift(1)
)

cleanlaps['DiffNext'] = (
    cleanlaps['CorrTime']
    - cleanlaps.groupby(['Driver', 'Stint'])['CorrTime'].shift(-1)
)

cleanlaps['IsSigWor'] = (
    (cleanlaps['DiffNext'] > 0.015 *
     cleanlaps.groupby(['Driver', 'Stint'])['CorrTime'].transform('median')) &
    (cleanlaps['DiffPrev'] > 0.015 *
     cleanlaps.groupby(['Driver', 'Stint'])['CorrTime'].transform('median'))
)

cleanlaps['TimeDiff'] = (
    cleanlaps.groupby(['Driver', 'Stint'])['CorrTime'].diff()
)

cleanlaps = cleanlaps[~cleanlaps['IsSigWor']]



cleanlaps.loc[:, 'StintLap'] = (
    cleanlaps.groupby(['Driver', 'Stint']).cumcount() + 1
)

cleanlaps = cleanlaps[cleanlaps['StintLap'] > 3]


# Keep slick compounds
slick_compounds = ['SOFT', 'MEDIUM', 'HARD']

cleanlaps = cleanlaps[
    cleanlaps['Compound'].isin(slick_compounds)
]


degradation_df = (
    cleanlaps.groupby(['Driver', 'Stint', 'Compound'])
    .apply(safe_polyfit, include_groups=False)
    .reset_index(name='DegradationRate')
)

degradation_df = degradation_df.dropna(
    subset=['DegradationRate']
)



print(degradation_df.to_string())


plot_driver_degradation(cleanlaps)

plot_compound_degradation(cleanlaps)
