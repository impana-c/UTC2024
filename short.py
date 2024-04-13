
from typing import Optional

from xchangelib import xchange_client
import asyncio
import random

# exchange: http://staging.uchicagotradingcompetition.com/
# Example bot: https://github.com/UChicagoFM/xchangelib/blob/move_repo/src/xchangelib/examples/example_bot.py
# Current strategies:
# 1 - Market make on theoretical value of mean or median
# 2 - Pairs trade?
# 3 - ETF arbitrage, swap fees of $5 so check if basket of stocks + $5 < ETF price
# Market make on ETF using theo value - Layer 1
# Arbitrage: if total cost of basket + 5 < theo etf value
# Cancel ALL unfilled orders after 3 seconds, every minute zero positions

# If 3 EPT (lowest ask) + 3 IGM (lowest ask) + 4 BRV (lowest ask) + $1 (edge) < 10 SCP (highest bid) ==> BUY basket of stocks, short 10 SCP?
class MyXchangeClient(xchange_client.XChangeClient):
    '''A shell client with the methods that can be implemented to interact with the xchange.'''

    swap_fee = 5.0
    edge = 0.97

    def __init__(self, host: str, username: str, password: str):
        super().__init__(host, username, password)

    async def spread(self, asset_name):
        """
        Asynchronously get the highest bid and the lowest ask for a specific asset,
        print the spread, and then return only the lowest ask.

        :param asset_name: The name of the asset to retrieve the lowest ask for.
        :return: The lowest ask for the given asset.
        """
        book = self.order_books.get(asset_name)

        if not book:
            print(f"{asset_name} not found in the order books.")
            return None

        if book.bids and book.asks:
            # Sort bids in descending order to get the highest bid.
            sorted_bids = sorted((k, v) for k, v in book.bids.items() if v != 0)
            highest_bid = sorted_bids[-1] if sorted_bids else None

            # Sort asks in ascending order to get the lowest ask.
            sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
            lowest_ask = sorted_asks[0] if sorted_asks else None

            if highest_bid and lowest_ask:
                # Convert the first element of the tuples to integers before calculating the spread.
                bid_price = int(highest_bid[0])
                ask_price = int(lowest_ask[0])
                spread = ask_price - bid_price
                # print(f"Spread for {asset_name} = {spread}")
                return lowest_ask[0], highest_bid[0]

        return None,None

    async def bot_handle_cancel_response(self, order_id: str, success: bool, error: Optional[str]) -> None:

        order = self.open_orders[order_id]
        print(f"{'Market' if order[2] else 'Limit'} Order ID {order_id} cancelled, {order[1]} unfilled")

    async def bot_handle_order_fill(self, order_id: str, qty: int, price: int):
        print("order fill", self.positions)

    async def bot_handle_order_rejected(self, order_id: str, reason: str) -> None:
        print("order rejected because of ", reason)

    async def bot_handle_trade_msg(self, symbol: str, price: int, qty: int):
        # print(f" {qty} {symbol} was traded at $ {price}")
        if (str == "IGM"):
            self.spread(self, "IGM")
        pass

    async def bot_handle_book_update(self, symbol: str) -> None:
        # print("book update")
        """await self.view_books()"""
        pass

    async def bot_handle_swap_response(self, swap: str, qty: int, success: bool):
        # print("Swap response")
        pass

    async def long_short_arbitrage(self):
        # Get the lowest asks for each stock
        ept_ask, _ = await self.spread("EPT")
        # print({ept_ask})
        dlo_ask, _ = await self.spread("DLO")
        # print({dlo_ask})
        mku_ask, _ = await self.spread("MKU")
        # print({mku_ask})
        igm_ask, _ = await self.spread("IGM")
        # print({igm_ask})
        brv_ask, _ = await self.spread("BRV")
        # print({brv_ask})
        _, scp_bid = await self.spread("SCP")
        _, jak_bid = await self.spread("JAK")

        # Calculate the total cost of buying the basket of stocks for ETF 1 and ETF 2
        if (ept_ask is not None and igm_ask is not None and brv_ask is not None and scp_bid is not None):
            total_stock_cost_scp = 3 * ept_ask + 3 * igm_ask + 4 * brv_ask 
            total_stock_cost_scp *= self.edge
            scp_diff = total_stock_cost_scp + self.swap_fee - (scp_bid * 10)
        else:
            scp_diff = None

        if (ept_ask is not None and dlo_ask is not None and mku_ask is not None and jak_bid is not None):
            total_stock_cost_jak = 2 * ept_ask + 5 * dlo_ask + 3 * mku_ask
            total_stock_cost_jak *= self.edge
            jak_diff = total_stock_cost_jak + self.swap_fee - (jak_bid * 10)
        else: 
            jak_diff = None

        # Returns positive values around $400 to $600
        if scp_diff is None:
            pass
        elif scp_diff < 0:
            print("short SCP")
            await self.place_order("SCP", 10, xchange_client.Side.SELL)
            # Buy the basket of stocks for ETF 1 (SCP)
            await self.place_order("EPT", 3, xchange_client.Side.BUY)
            await self.place_order("IGM", 3, xchange_client.Side.BUY)
            await self.place_order("BRV", 4, xchange_client.Side.BUY)
        elif scp_diff > 0:
            print("long SCP")
            await self.place_order("SCP", 10, xchange_client.Side.BUY)
            # Buy the basket of stocks for ETF 1 (SCP)
            await self.place_order("EPT", 3, xchange_client.Side.SELL)
            await self.place_order("IGM", 3, xchange_client.Side.SELL)
            await self.place_order("BRV", 4, xchange_client.Side.SELL)

        if jak_diff is None:
            pass
        elif jak_diff < 0:
            print("short JAK")
            await self.place_order("JAK", 10, xchange_client.Side.SELL)
            # Buy the basket of stocks for ETF 2 (JAK)
            await self.place_order("EPT", 2, xchange_client.Side.BUY)
            await self.place_order("DLO", 5, xchange_client.Side.BUY)
            await self.place_order("MKU", 3, xchange_client.Side.BUY)
        elif jak_diff > 0:
            print("long JAK")
            await self.place_order("JAK", 10, xchange_client.Side.BUY)
            # Buy the basket of stocks for ETF 2 (JAK)
            await self.place_order("EPT", 2, xchange_client.Side.SELL)
            await self.place_order("DLO", 5, xchange_client.Side.SELL)
            await self.place_order("MKU", 3, xchange_client.Side.SELL)

    async def firesale(self):
        # Sells everything, good for end of round / algo?
        await asyncio.sleep(5)
        print("Attempting to sell everything")

        # Sell all long positions
        for symbol, position in self.positions.items():
            lowest_ask, highest_bid = await self.spread(symbol)
            if position > 0 and symbol != 'cash' and lowest_ask is not None and highest_bid is not None:  # Ignore 'cash' position
                if abs(position) > 40:
                    mod = abs(position) % 40
                    iter = int(abs(position) / 40)
                    for i in range(iter):
                        order_id = await self.place_order(symbol, 40, xchange_client.Side.SELL, highest_bid - 50)
                        print(f"Placed sell order for {40} shares of {symbol} (Long) - Order ID: {order_id}")
                    order_id = await self.place_order(symbol, mod, xchange_client.Side.SELL, highest_bid - 50)
                    print(f"Placed sell order for {mod} shares of {symbol} (Long) - Order ID: {order_id}")
                else:
                    order_id = await self.place_order(symbol, abs(position), xchange_client.Side.SELL, highest_bid - 50)
                    print(f"Placed sell order for {abs(position)} shares of {symbol} (Long) - Order ID: {order_id}")
                await asyncio.sleep(0.05)

        # Buy back short positions
        for symbol, position in self.positions.items():
            lowest_ask, highest_bid = await self.spread(symbol)
            if position < 0 and symbol != 'cash' and lowest_ask is not None and highest_bid is not None:  # Ignore 'cash' position
                if abs(position) > 40:
                    mod = abs(position) % 40
                    iter = int(abs(position) / 40)
                    for i in range(iter):
                        order_id = await self.place_order(symbol, 40, xchange_client.Side.BUY, lowest_ask + 50)
                        print(f"Placed buy order for {40} shares of {symbol} (Long) - Order ID: {order_id}")
                    order_id = await self.place_order(symbol, mod, xchange_client.Side.BUY + lowest_ask + 50)
                    print(f"Placed buy order for {mod} shares of {symbol} (Long) - Order ID: {order_id}")
                else:
                    order_id = await self.place_order(symbol, abs(position), xchange_client.Side.BUY + lowest_ask + 50)
                    print(f"Placed buy order for {abs(position)} shares of {symbol} (Long) - Order ID: {order_id}")
                await asyncio.sleep(0.05)
        print("All positions have been sold")
    
    async def do_stuff(self):
        for i in range(5):
            lowest_ask_dlo, highest_bid_dlo = await self.spread('DLO')
            if (highest_bid_dlo != None):
                await self.place_order('DLO',40, xchange_client.Side.SELL, highest_bid_dlo - 50)

            lowest_ask_ept, highest_bid_ept = await self.spread('EPT')
            if (highest_bid_ept != None):
                await self.place_order('EPT',40, xchange_client.Side.SELL, highest_bid_ept - 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('JAK')
            if (highest_bid_jak != None):
                await self.place_order('JAK',40, xchange_client.Side.SELL, highest_bid_jak - 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('IGM')
            if (lowest_ask_jak != None):
                await self.place_order('IGM',40, xchange_client.Side.BUY, lowest_ask_jak + 50)
            
            await asyncio.sleep(0.1)

    async def clear_stuff(self):
        for i in range(5):
            lowest_ask_dlo, highest_bid_dlo = await self.spread('DLO')
            if (highest_bid_dlo != None):
                await self.place_order('DLO',40, xchange_client.Side.BUY, lowest_ask_dlo + 50)

            lowest_ask_ept, highest_bid_ept = await self.spread('EPT')
            if (highest_bid_ept != None):
                await self.place_order('EPT',40, xchange_client.Side.BUY, lowest_ask_ept + 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('JAK')
            if (highest_bid_jak != None):
                await self.place_order('JAK',40, xchange_client.Side.BUY, lowest_ask_jak + 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('IGM')
            if (lowest_ask_jak != None):
                await self.place_order('IGM',40, xchange_client.Side.SELL, highest_bid_jak - 50)
            
            await asyncio.sleep(0.1)

    async def trade(self):
        """This is a task that is started right before the bot connects and runs in the background."""
        await asyncio.sleep(2)
        print("Bot started")

        """Places strategic bid and ask orders for 'EPT' based on the current market conditions."""
        stock_long = ['IGM', 'BRV', 'SCP']
        stock_short = ['EPT', 'DLO', 'MKU']
        stock_symbols = ['BRV', 'DLO', 'EPT', 'IGM', 'MKU', 'JMS', 'JAK','SCP']

        await self.do_stuff()

        # await self.clear_stuff()


        # await self.place_order('DLO',10, xchange_client.Side.BUY)
        # while True:  # Loop to place orders repeatedly
        #     for stock in stock_symbols:
        #         # Get the current highest bid and lowest ask for the stock
        #         # rng = random.randint(0, 1)
        #         rng=1
        #         if rng == 0:
        #             pass
        #             await self.place_order(stock,10, xchange_client.Side.SELL)
        #             await asyncio.sleep(0.02)
        #         else:
        #             await self.place_order(stock, 5, xchange_client.Side.BUY)
        #             await asyncio.sleep(0.01)
        #     # await asyncio.sleep(2)
        #         # await self.place_order('IGM', 5, xchange_client.Side.BUY)

        #         # lowest_ask, highest_bid = await self.spread(stock)
        
        # lowest_ask_brv, highest_bid_brv = await self.spread('BRV')
        # await self.place_order('BRV',20, xchange_client.Side.BUY, lowest_ask_brv + 50)

        # lowest_ask_ept, highest_bid_ept = await self.spread('EPT')
        # if (highest_bid_ept != None):
        #     await self.place_order('EPT',40, xchange_client.Side.SELL, highest_bid_ept - 50)

        ##FIRESALE
        # for i in range(5):
        #     lowest_ask_dlo, highest_bid_dlo = await self.spread('DLO')
        #     if (highest_bid_dlo != None):
        #         await self.place_order('DLO',40, xchange_client.Side.BUY, lowest_ask_dlo + 50)

        #     lowest_ask_ept, highest_bid_ept = await self.spread('EPT')
        #     if (highest_bid_ept != None):
        #         await self.place_order('EPT',40, xchange_client.Side.BUY, lowest_ask_ept + 50)
            
        #     lowest_ask_jak, highest_bid_jak = await self.spread('JAK')
        #     if (highest_bid_jak != None):
        #         await self.place_order('JAK',40, xchange_client.Side.BUY, lowest_ask_jak + 50)
            
        #     lowest_ask_jak, highest_bid_jak = await self.spread('IGM')
        #     if (lowest_ask_jak != None):
        #         await self.place_order('IGM',40, xchange_client.Side.SELL, highest_bid_jak - 50)
            
        #     await asyncio.sleep(0.1)

        ##ALGO
        for i in range(5):
            lowest_ask_dlo, highest_bid_dlo = await self.spread('DLO')
            if (highest_bid_dlo != None):
                await self.place_order('DLO',40, xchange_client.Side.SELL, highest_bid_dlo - 50)

            lowest_ask_ept, highest_bid_ept = await self.spread('EPT')
            if (highest_bid_ept != None):
                await self.place_order('EPT',40, xchange_client.Side.SELL, highest_bid_ept - 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('JAK')
            if (highest_bid_jak != None):
                await self.place_order('JAK',40, xchange_client.Side.SELL, highest_bid_jak - 50)
            
            lowest_ask_jak, highest_bid_jak = await self.spread('IGM')
            if (lowest_ask_jak != None):
                await self.place_order('IGM',40, xchange_client.Side.BUY, lowest_ask_jak + 50)
            
            await asyncio.sleep(0.1)

            
            # for sl in stock_long:
            #     lowest_bid, highest_ask = await self.spread(sl)
            #     await self.place_order(sl,10, xchange_client.Side.BUY)
            #     await asyncio.sleep(0.1)
            
            # for ss in stock_short:
            #     lowest_bid, highest_ask = await self.spread(sl)
            #     await self.place_order(sl,10, xchange_client.Side.SELL)
            #     await asyncio.sleep(0.1)




            #     if highest_bid is not None:
            #         # Place a bid order $10 below the highest bid
            #         bid_price = highest_bid - 10
            #         await self.place_order(stock, 3, xchange_client.Side.BUY, bid_price)
            #         await asyncio.sleep(0.05)
            #         # await self.place_order(stock,3, xchange_client.Side.SELL,highest_bid)

            #     if lowest_ask is not None:
            #         # Place an ask order $10 above the lowest ask
            #         ask_price = lowest_ask + 10
            #         await self.place_order(stock, 3, xchange_client.Side.SELL, ask_price)
            #         await asyncio.sleep(0.05)
            #         #nawait self.place_order(stock, 3, xchange_client.Side.BUY,lowest_ask)
            #     await asyncio.sleep(0.05)

            # await asyncio.sleep(0.05)  # Sleep to rate limit the orders
        
        """
        
        # await self.firesale()
        for i in range(100):
            # check if we reach the limit of absolute position
            for symbol, position in self.positions.items():
                if abs(position) == 200 and symbol != 'cash':
                    await self.firesale()
            await self.long_short_arbitrage()
            await asyncio.sleep(2)
        await self.firesale()


        # Place market order for individual ETF items
        await self.place_order("EPT",3, xchange_client.Side.BUY)
        await asyncio.sleep(5)
        await self.place_order("EPT",3, xchange_client.Side.SELL)
        await asyncio.sleep(5)

        await self.place_order("IGM", 3, xchange_client.Side.BUY)
        await asyncio.sleep(5)

        await self.place_order("BRV", 4, xchange_client.Side.BUY)
        await asyncio.sleep(5)

        print("Bot bought basket")

        # Swap the stocks into 10 SCP etfs
        await self.place_swap_order('toSCP', 1)
        await asyncio.sleep(5)

        # Viewing Positions
        print("My positions:", self.positions)

        # Sell the 10 SCP etfs
        await self.place_order("SCP",10,xchange_client.Side.SELL)
        await asyncio.sleep(5)

        # View positions again
        print("My positions:", self.positions)

        # Now do opposite, buy 10 ETFs then redeem for individual stocks
        await self.place_order("SCP",10,xchange_client.Side.BUY)
        await asyncio.sleep(5)

        # Now swap and then sell individual stocks
        await self.place_swap_order('fromSCP',1)
        await asyncio.sleep(5)

        await self.firesale()
        """

    async def view_books(self):
        """Prints the books every 3 seconds."""
        while True:
            await asyncio.sleep(3)
            for security, book in self.order_books.items():
                sorted_bids = sorted((k, v) for k, v in book.bids.items() if v != 0)
                sorted_asks = sorted((k, v) for k, v in book.asks.items() if v != 0)
                print(f"Bids for {security}:\n{sorted_bids}")
                print(f"Asks for {security}:\n{sorted_asks}")

    """
    async def view_book_for(self, sec: str):
        while True:
            await asyncio.sleep(3)
            for sec, book in self.order_books.items():
                sorted_bids = sorted((k,v) for k,v in book.bids.items() if v != 0)
                sorted_asks = sorted((k,v) for k,v in book.asks.items() if v != 0)
                print(f"Bids for {sec}:\n{sorted_bids}")
                print(f"Asks for {sec}:\n{sorted_asks}")
    """

    async def start(self):
        """
        Creates tasks that can be run in the background. Then connects to the exchange
        and listens for messages.
        """
        asyncio.create_task(self.trade())
        # asyncio.create_task(self.view_books())
        await self.connect()


async def main():
    SERVER = 'dayof.uchicagotradingcompetition.com:3333'  # run on sandbox
    my_client = MyXchangeClient(SERVER, "ucla", "alakazam-ponyta-4981")
    await my_client.start()
    return


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())
