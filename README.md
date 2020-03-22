Tracks ERC transfers, notifies users of large transactions on the netowrk. 
Coins being tracked at ERC20 located in the coin_addresses.json file.

Transaction size are calculated based on liquidity of each token on Uniswap.
More specifically, it calculates the transaction volume required to generate 10% slippage.

Soon to come:
- Support to more DEXes
- User profiles to set notification settings based on destination addresses and coin
- Filter implementation to run backtests and agg data
- Simulated impact of tx amount vs market impact
