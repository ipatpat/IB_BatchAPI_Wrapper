from ib_async import *
# util.startLoop()  # uncomment this line when in a notebook

ib = IB()
ib.connect('127.0.0.1', 4002, clientId=1)

# Request historical data
contract = Stock('AAPL', 'SMART', 'USD', primaryExchange='NASDAQ')
bars = ib.reqHistoricalData(
    contract, endDateTime='', durationStr='8 Y',
    barSizeSetting='15 mins', whatToShow='TRADES', useRTH=True, timeout=3600)

# Convert to pandas dataframe (pandas needs to be installed):
df = util.df(bars)
print(df.head())

ib.disconnect()