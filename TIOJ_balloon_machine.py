"""TIOJ Balloon Machine"""

import asyncio
from bs4 import BeautifulSoup
import discord
import requests

from config import *

session = requests.Session()

contest_id = int(input('Contest ID: '))
url = judge_site + '/contests/{}/dashboard'.format(contest_id)

rel = session.get(url)
soup = BeautifulSoup(rel.text, "html.parser")
cols = soup.find_all('th')

task_columns = []
for i, th in enumerate(cols):
    a = th.find('a')
    if a and a.string.startswith('p'):
        task_columns.append((i, a.string))
assert len(task_columns)
print("Started balloon machine for Contest {} with {} tasks".format(contest_id, len(task_columns)))

def get_users_AC_list():
    rel = session.get(url)
    soup = BeautifulSoup(rel.text, "html.parser")
    rows = soup.find_all('tr')

    users_AC_list = {}
    for row in rows[1:]:
        cols = row.find_all('td')
        username = cols[2].string
        flag = False
        for prefix in banned_prefix:
            if username.startswith(prefix): flag = True
        if flag: continue
        AC_list = []
        for col_number, task_label in task_columns:
            content = cols[col_number].get_text()
            if content.find('/') != -1:
                AC_list.append(task_label)
        users_AC_list[username] = AC_list
    return users_AC_list

class BalloonMachineBot(discord.Client):
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        self.channel = self.get_channel(DISCORD_CHANNEL_ID)
        self.loop.create_task(self.main())

    async def on_reaction_add(self, reaction, user):
        emoji = reaction.emoji
        if user == self.user: return;
        if emoji == DONE_EMOJI:
            message = reaction.message
            await message.clear_reaction(DONE_EMOJI)
            content = message.content
            paran = content.find('(')
            if paran > 0:
                content = content[:paran - 1]
            await message.edit(content=content + " (Delivered by {})".format(user.name))
            # await reaction.message.delete()
        elif emoji == CLAIM_EMOJI:
            message = reaction.message
            await message.clear_reaction(CLAIM_EMOJI)
            await message.add_reaction(DONE_EMOJI)
            await message.edit(content=message.content + " (Claimed by {})".format(user.name))

    async def send_AC_message(self, content):
        message = await self.channel.send(content)
        await message.add_reaction(CLAIM_EMOJI)

    async def new_AC(self, username, task_label):
        print("New AC: {} - {}".format(username, task_label))
        await self.send_AC_message("`{}` - **{}**".format(username, task_label))

    async def main(self):
        saved_users_AC_list = {}
        initial_list = get_users_AC_list()
        if len(initial_list):
            res = input("The scoreboard seems not empty. Resend all balloons? (y/Y/n/N): ").strip()
            if res == 'n' or res == 'N':
                saved_users_AC_list = initial_list
            else:
                assert res == 'y' or res == 'Y'

        while True:
            try:
                users_AC_list = get_users_AC_list()
                for username in users_AC_list:
                    for task_label in users_AC_list[username]:
                        if username not in saved_users_AC_list or task_label not in saved_users_AC_list[username]:
                            await self.new_AC(username, task_label)
                saved_users_AC_list = users_AC_list
                await asyncio.sleep(seconds_between_fetch)
            except KeyboardInterrupt:
                exit(0)
            except Exception as e:
                print('{}: {}'.format(type(e).__name__, e))

bot_client = BalloonMachineBot()
bot_client.run(DISCORD_TOKEN)
