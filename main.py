from typing import Optional

from xchangelib import xchange_client
import asyncio




class MyXchangeClient(xchange_client.XChangeClient):
    '''A shell client with the methods that can be implemented to interact with the xchange.'''

    def __init__(self, host: str, username: str, password: str):
        super().__init__(host, username, password)

    async def bot_handle_cancel_response(self, order_id: str, success: bool, error: Optional[str]) -> None:

        order = self.open_orders[order_id]
        print(f"{'Market' if order[2] else 'Limit'} Order ID {order_id} cancelled, {order[1]} unfilled")

    async def bot_handle_order_fill(self, order_id: str, qty: int, price: int):
        print("order fill", self.positions)

    async def bot_handle_order_rejected(self, order_id: str, reason: str) -> None:
        print("order rejected because of ", reason)


    async def bot_handle_trade_msg(self, symbol: str, price: int, qty: int):
        print(f" {qty} {symbol} was traded at $ {price}")
        pass

    async def bot_handle_book_update(self, symbol: str) -> None:
        # print("book update")
        await self.view_books()
        pass

    async def bot_handle_swap_response(self, swap: str, qty: int, success: bool):
        # print("Swap response")
        pass

    async def firesale(self):
        # Sells everything, good for end of round / algo?
        await asyncio.sleep(5)
        print("Attempting to sell everything")

        # Sell all long positions
        for symbol, position in self.positions.items():
            if position > 0 and symbol != 'cash':  # Ignore 'cash' position
                order_id = await self.place_order(symbol, abs(position), xchange_client.Side.SELL)
                print(f"Placed sell order for {abs(position)} shares of {symbol} (Long) - Order ID: {order_id}")
                await asyncio.sleep(5)

        # Sell all short positions
        for symbol, position in self.positions.items():
            if position < 0 and symbol != 'cash':  # Ignore 'cash' position
                order_id = await self.place_order(symbol, abs(position), xchange_client.Side.BUY)
                print(f"Placed sell order for {abs(position)} shares of {symbol} (Short) - Order ID: {order_id}")
                await asyncio.sleep(5)
    print("All positions have been sold")


    async def trade(self):
        """This is a task that is started right before the bot connects and runs in the background."""
        await asyncio.sleep(5)
        print("Bot started")
        '''
        # Place market order for individual ETF items
        await self.place_order("EPT",3, xchange_client.Side.BUY)
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
        print("My positions:", self.positions)  '''

        # Now do opposite, buy 10 ETFs then redeem for individual stocks
        await self.place_order("SCP",10,xchange_client.Side.BUY)
        await asyncio.sleep(5)

        # Now swap and then sell individual stocks
        await self.place_swap_order('fromSCP',1)
        await asyncio.sleep(5)

        await self.firesale()


    async def view_books(self):
        """Prints the books every 3 seconds."""
        while True:
            await asyncio.sleep(3)
            for security, book in self.order_books.items():
                sorted_bids = sorted((k,v) for k,v in book.bids.items() if v != 0)
                sorted_asks = sorted((k,v) for k,v in book.asks.items() if v != 0)
                print(f"Bids for {security}:\n{sorted_bids}")
                print(f"Asks for {security}:\n{sorted_asks}")

    async def view_book_for(self, sec: str):
        """Prints the books every 3 seconds."""
        while True:
            await asyncio.sleep(3)
            for sec, book in self.order_books.items():
                sorted_bids = sorted((k,v) for k,v in book.bids.items() if v != 0)
                sorted_asks = sorted((k,v) for k,v in book.asks.items() if v != 0)
                print(f"Bids for {sec}:\n{sorted_bids}")
                print(f"Asks for {sec}:\n{sorted_asks}")

    async def start(self):
        """
        Creates tasks that can be run in the background. Then connects to the exchange
        and listens for messages.
        """
        asyncio.create_task(self.trade())
        # asyncio.create_task(self.view_books())
        await self.connect()


async def main():
    SERVER = 'staging.uchicagotradingcompetition.com:3333' # run on sandbox
    my_client = MyXchangeClient(SERVER,"ucla","alakazam-ponyta-4981")
    await my_client.start()
    return

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(main())