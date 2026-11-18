def safe_polyfit(group):

  g_clean = group.dropna(subset=['TyreLife', 'CorrTime'])

  if len(g_clean) < 2 or g_clean['TyreLife'].nunique() < 2:
    return np.nan
  slope, intercept = np.polyfit(g_clean['TyreLife'], g_clean['CorrTime'], 1)
  if slope<0:
      return np.nan

  return slope



import fastf1 as ff1
import os
import matplotlib as mpl
import pandas as pd
import numpy as np
from pandas._libs.tslibs.offsets import Nano

os.makedirs('cache', exist_ok=True)
ff1.Cache.configure(cache_dir='cache')
#email=input("Enter your email here ")
#password=input("Enter your password here ")
email='szymon.f.sto@gmail.com'
password='Sajlol123#'
os.environ['F1_USERNAME'] = email
os.environ['F1_PASSWORD'] = password

year = int(input("Give year of the GP "))
round_identifier = input(
    "Give the name of the track (e.g. 'Monza') or the round number (e.g. 20)"
)

if round_identifier.isdigit():
  round_identifier = int(round_identifier)

session = ff1.get_session(year, round_identifier, 'R')
session.load()
laps = session.laps




print(laps.columns)
print(laps.info())

laps['LapSecondTime']=laps['LapTime'].dt.total_seconds()


laps['FuelUsage']=np.where( laps['TrackStatus'].str.contains('4|6|7'),0.6, 1.65)

conditions = [
    laps['TrackStatus'].str.contains('5'),
    laps['TrackStatus'].str.contains('4|6|7')
]
values = [0.1, 0.6]
laps['FuelUsage'] = np.select(conditions, values, default=1.65)
laps['UsedFuel']=laps.groupby(['Driver'])['FuelUsage'].cumsum()-laps['FuelUsage']
laps['UsedFuel']=laps['UsedFuel'].fillna(0)


laps['PredFuelUsageOnLap'] =1.65
laps['PredUsedFuel']=laps.groupby(['Driver'])['PredFuelUsageOnLap'].cumsum()-laps['PredFuelUsageOnLap']
FuelWeight=laps['PredUsedFuel'].max()+1.75 #Safety Reserve
mass_sensitivity = 0.032
laps['CorrTime']=laps['LapSecondTime']-mass_sensitivity*(FuelWeight-laps['UsedFuel'])
laps['MedianTime']=laps.groupby('LapNumber')['CorrTime'].transform('median')
base_median = np.nan
for lap_num in sorted(laps['LapNumber'].unique()):
  subset = laps.loc[laps['LapNumber'] == lap_num, 'MedianTime']
  if not subset.dropna().empty:
    base_median = subset.dropna().iloc[0]
    break
laps['CorrTime']=laps['CorrTime']+(base_median-laps['MedianTime'])

cleanlaps=laps[
(laps['PitInTime'].isnull())&
(laps['PitOutTime'].isnull())&
(~laps['TrackStatus'].str.contains('4|5|6|7'))&
(laps['LapNumber']>1)&
(laps['Compound'].str.contains('SOFT|MEDIUM|HARD'))
][['LapNumber','PitInTime','Driver','Compound','TyreLife','TrackStatus','CorrTime','Stint']]
cleanlaps['DiffPrev']=cleanlaps['CorrTime']-cleanlaps.groupby(['Driver','Stint'])['CorrTime'].shift(1)
cleanlaps['DiffNext']=cleanlaps['CorrTime']-cleanlaps.groupby(['Driver','Stint'])['CorrTime'].shift(-1)
cleanlaps['IsSigWor']=((cleanlaps['DiffNext']>0.015*cleanlaps.groupby(['Driver','Stint'])['CorrTime'].transform('median')) &
                       (cleanlaps['DiffPrev']>0.015*cleanlaps.groupby(['Driver','Stint'])['CorrTime'].transform('median')))
cleanlaps['TimeDiff'] = cleanlaps.groupby(['Driver','Stint'])['CorrTime'].diff()
cleanlaps = cleanlaps[~cleanlaps['IsSigWor']]

cleanlaps.loc[:, 'StintLap'] = (
    cleanlaps.groupby(['Driver', 'Stint']).cumcount() + 1
)
cleanlaps=cleanlaps[cleanlaps['StintLap']>3]

slick_compounds = ['SOFT', 'MEDIUM', 'HARD']
cleanlaps = cleanlaps[cleanlaps['Compound'].isin(slick_compounds)]

degradation_df = (
    cleanlaps.groupby(['Driver', 'Stint', 'Compound'])
    .apply(safe_polyfit,include_groups=False)
    .reset_index(name='DegradationRate')
)

degradation_df = degradation_df.dropna(subset=['DegradationRate'])

print(degradation_df.to_string())
#print(laps.to_string())
#print(cleanlaps.to_string())