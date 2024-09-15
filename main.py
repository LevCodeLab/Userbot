from telethon import TelegramClient, events
from telethon.sessions import StringSession
import os
import json
import requests
import asyncio
import time

# Replace with your own values from my.telegram.org and BotFather
api_id = 22855880  # Your App API ID
api_hash = '94be7796163a78b7c57666ea89fd9e61'  # Your App API Hash
phone_number = '+918423272388'  # Your phone number (hardcoded)
bot_token = '6864501211:AAFAFJMxuppCylD2gIaqJsiZD6guO4uwMKM'  # Your BotFather's bot token
record_group_username = 'https://t.me/recordgroupb'  # Correct username
session_file_path = 'session.json'  # Session file path

# Load session if it exists
if os.path.exists(session_file_path):
    with open(session_file_path, 'r') as f:
        session_info = json.load(f)
        session_string = session_info['session']
else:
    session_string = None

# Create a Telegram client for user account and bot
user_client = TelegramClient(StringSession(session_string), api_id, api_hash)
bot_client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

def format_value(value):
    """Formats the value into K or M."""
    if value >= 1e6:  # 1,000,000
        return f"{value / 1e6:.2f}M"
    elif value >= 1e3:  # 1,000
        return f"{value / 1e3:.2f}K"
    else:
        return str(value)

async def fetch_dex_data(contract_address):
    """
    Fetch data from the DexScreener API for the given contract address.
    Returns the fdv and liquidity values.
    """
    url = f'https://api.dexscreener.com/latest/dex/search?q={contract_address}'
    try:
        response = requests.get(url)
        data = response.json()
        if 'pairs' in data and len(data['pairs']) > 0:
            pair = data['pairs'][0]
            fdv = pair['fdv']
            liquidity = pair['liquidity']['usd']
            return fdv, liquidity
    except Exception as e:
        print("Error fetching data from DexScreener:", e)
    return None, None

@user_client.on(events.NewMessage)
async def handler(event):
    # Check if the message starts with "/buy"
    if event.message.message.startswith('/buy'):
        contract_address = event.message.message.split()[1]

        # Fetch Dex data
        fdv, liquidity = await fetch_dex_data(contract_address)
        if fdv is None or liquidity is None:
            await user_client.send_message(event.chat_id, "Failed to fetch data!")
            return

        # Convert FDV and Liquidity to desired format
        formatted_fdv = format_value(fdv)
        formatted_liquidity = format_value(liquidity)

        # Store the initial FDV for multiplier calculation
        initial_fdv = fdv

        # Update the original /buy message
        await event.message.edit(f"Buy recorded at FDV: {formatted_fdv}")

        # Prepare the initial report message for the bot to send
        report_msg_content = (
            f"Buy Recorded At: {event.chat.title}\n\n"
            f"FDV: {formatted_fdv}\n"
            f"Liquidity: {formatted_liquidity}\n\n"
            f"Current FDV: {formatted_fdv}\n"  # Initial current FDV is the same as initial FDV
            f"We Are At: 1.0X\n"
            f"Last Updated: {time.strftime('%H:%M || %d %b')}\n"
        )

        try:
            # Send the message to the record group
            record_message = await bot_client.send_message(record_group_username, report_msg_content)
        except Exception as e:
            print(f"Failed to send message to {record_group_username}. Error: {str(e)}")
            return  # Exit if we can't send the message

        # Update current values every 30 seconds
        while True:
            await asyncio.sleep(30)
            current_fdv, current_liquidity = await fetch_dex_data(contract_address)
            if current_fdv is None:
                break  # Exit the loop if there's an error

            # Update formatted values
            formatted_current_fdv = format_value(current_fdv)

            # Calculate the multiplier (X)
            multiplier = current_fdv / initial_fdv if initial_fdv != 0 else 0
            multiplier_str = f"{multiplier:.2f}X"

            # Prepare updated message content
            updated_msg_content = (
                f"Buy Recorded At: {event.chat.title}\n\n"
                f"FDV: {formatted_fdv}\n"
                f"Liquidity: {formatted_liquidity}\n\n"
                f"Current FDV: {formatted_current_fdv}\n"
                f"We Are At: {multiplier_str}\n"
                f"Last Updated: {time.strftime('%H:%M || %d %b')}\n"
            )

            try:
                # Edit the existing message
                await bot_client.edit_message(record_message, updated_msg_content)
            except Exception as e:
                print(f"Failed to update message in {record_group_username}. Error: {str(e)}")

async def main():
    # Start both the user client and bot
    await user_client.start(phone=phone_number)
    await bot_client.start()
    print("You are now connected to Telegram!")

    # Save the user session string to a file
    session_string = user_client.session.save()
    with open(session_file_path, 'w') as f:
        json.dump({'session': session_string}, f)
    print('Session information saved!')

    # Run the client until disconnected
    await user_client.run_until_disconnected()

# Run the main function
if __name__ == '__main__':
    with user_client:
        user_client.loop.run_until_complete(main())