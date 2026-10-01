#!/usr/bin/env python3
"""Send newsletter to Telegram bot"""

import os
from pathlib import Path
import telegram
import asyncio

async def main():
    # Newsletter content
    news_content = """# News Brief
*2026-09-19 21:18*

---

## 🔬 Science

**Arsenal suffers first loss:** Brighton dominated Arsenal 3-0 at Amex Stadium, handing the defending champions their first defeat this season and first loss by more than two goals in over three years. Manager Mikel Arteta admitted his side failed basic Premier League requirements.

**Sheeran addresses Gaza controversy:** Ed Sheeran apologized to Philadelphia concertgoers for "making mistakes" after dropping opening act Macklemore over pro-Palestinian remarks, calling the Gaza situation "catastrophic and unjustifiable." The singer said he never wanted to be an activist but was forced into the debate over free speech.

**Australia pushes tech regulation:** Prime Minister Anthony Albanese met Apple CEO Tim Cook in California seeking big tech cooperation on strengthened online safety laws and AI regulations, stating "Australia can't do it alone" on protecting children. The government is pursuing stricter rules including doubled fines and an under-16 social media ban.

**Congo launches Ebola vaccine trials:** DR Congo began administering the Ervebo vaccine to frontline health workers to combat the current Ebola outbreak. Officials hope the vaccine, effective in previous outbreaks, works against the present strain.

---

## 🤖 AI & Tech

**Chinese man sues AI firm over chatbot burial date advice:** A Zhejiang resident filed a lawsuit after following an AI chatbot's recommended "auspicious" burial date for his mother, which he claims preceded family misfortune. The case highlights growing legal questions around liability for AI-generated advice in culturally sensitive contexts.

**Researchers bypass RP2350 secure boot with laser fault injection:** Ledger Donjon security team used a $250,000 laser setup to target a specific register enabling debug features on Raspberry Pi's RP2350 microcontroller. The attack required decapsulating the chip and precise infrared laser targeting to overcome glitch detection protections.

---

## 🌍 World

**Ukraine condemns Russian elections in annexed regions:** Kyiv and the European Commission denounce Russia's inclusion of four partially occupied Ukrainian regions in its parliamentary elections as a blatant violation of international law. The vote proceeds on day 1,670 of the war despite universal non-recognition of Russia's annexation claims.

**DOJ charges 16 individuals with election crimes across eight states:** Federal prosecutors allege eight noncitizens in Texas voted in federal elections, with additional cases in Idaho, Georgia, Massachusetts, Wisconsin, New Jersey, and Michigan involving illegal registration and false citizenship claims. The department issued a public warning against further attempts to undermine U.S. elections.

**Suicide bombing in northwestern Pakistan kills dozens:** Tehrik-e-Taliban Pakistan claimed responsibility for a mosque attack in a northwestern city, continuing a two-decade pattern of violence Islamabad says originates from Afghan territory. The incident further strains Pakistan-Afghanistan relations as the government faces pressure to address cross-border militant sanctuaries.

**Canada joins fighter jet program as observer, signaling potential purchase:** Ottawa's observer status in the multinational combat aircraft program opens the door to future procurement while partner nations seek expanded export markets and deeper defense cooperation among aligned countries."""

    # Load Telegram configuration
    env_path = str(Path(os.path.expanduser("~/.hermes/.env")))
    with open(env_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

    # Get Telegram settings
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id_str = os.environ.get('TELEGRAM_ALLOWED_USERS', '1234567890')
    chat_id = int(chat_id_str)

    print(f"Sending to chat_id: {chat_id}")

    if bot_token and chat_id:
        bot = telegram.Bot(token=bot_token)
        
        # Send test message first
        test_msg = "Testing Telegram connection"
        try:
            result = await bot.send_message(chat_id=chat_id, text=test_msg)
            print(f"✓ Test message sent successfully")
        except Exception as e:
            print(f"✗ Test message failed: {e}")
            return
            
        # Now send the full newsletter content
        result = await bot.send_message(chat_id=chat_id, text=news_content)
        print(f"✓ Newsletter sent successfully: {result}")
    else:
        print(f"ERROR: bot_token={bool(bot_token)}, chat_id={chat_id}")

if __name__ == '__main__':
    asyncio.run(main())
