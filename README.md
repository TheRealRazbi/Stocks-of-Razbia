# Stocks of Razbia
It has been remade from scratch and moved to a private repository and it is now closed-source.
Right now it is a discord and twitch minigame. 


You can play it on twitch at twitch.tv/swavyl (this is not my twitch). 
If you want to get in touch with me for any reason (such as adding the bot to your own channel), go on twitch, use !suggestions and you can find a link to the discord server of the bot.

# READ ABOVE ^
# Stocks of Razbia
Welcome, Stocks of Razbia is a stock exchange simulation simplified to work on a twitch chat. <br>
This project was made by Razbi and Nesami.

## Installation
Here are the releases: https://github.com/TheRealRazbi/Stocks-of-Razbia/releases <br>
As long as you read the Notes on each release, before installing it, you should be fine.

## How does it work?
### Each 10 mins:

- 2 companies spawn until they reach 7 companies in total
- price of each existing company goes up or down randomly
- users gain points equal to 10% of the value of the stocks they own [this value gets decreased by 1% for each 10k stocks owned on a "per-company" basis. min 1%]
- companies, the users have stocks at, are slightly more likely to gain more money

### Basic Commands:

- !stocks | displays all the basic commands
- !autoinvest &lt;budget&gt; | buy random stocks whose value approach the budget value
- !buy &lt;company&gt; &lt;amount&gt; | amount is a number
- !sell &lt;company&gt; &lt;amount&gt; | amount is a number or 'all'
- !companies | display all companies
- !company &lt;company&gt; | show info about a company such as full-name and price

### Extra commands:

- !sell_everything | same as !sell, but on ALL your owned stocks
- !my stats | displays your shares + income + profit
- !my shares | displays all the shares you own
- !my profit | it will show you all the profit from all points invested [doesn't take into account the value of current shares]
- !my points | shows your points [in case the minigame uses a different currency system than streamer's]
- !my income | shows your income from all companies
- !introduction | displays a link to the Introduction document, which is a close copy to this one
- !about | displays the dev names and the github link
- !all commands | displays literally ALL the commands

### Note:
The minigame and all companies are hosted locally.
As this is currently in the testing version, everything is subject to change.

### Event System:
Each 4 months, a company [usually with fewest owned stocks] gets picked for a positive event.
The event is announced and it increase the chance of that company making making, by 5-20% for 2-4 months.

### Supports:
 
- Fully customizable Command Names, Command Outputs and Announcements
- Streamlabs Extension Currency
- StreamElements Currency
- Streamlabs Chatbot Local Currency
- Streamlabs Cloudbot [not yet, because it has no API support, so it will require webscrapping from my end]
- Fully Local Currency [not yet, I will add it whenever Streamers will ask for it]

## Contributions:

Discord server: https://discord.gg/yp3T7da <br>
Currently any testing is greatly appreciated. For feedback/questions please visit the discord server.<br>