Fumo-DiscordBot
===============

A Discord bot with fun commands made with discord.py inspired by high-quality plush Touhou Project character figures.

----

Invite the bot!
---------------
https://discord.com/oauth2/authorize?client_id=890596157699526686&scope=bot+applications.commands&permissions=274878286912

----

Self-Hosting
------------

| I would rather you inviting the bot itself. However, if you want to self-host the bot, here's how to do it:
| (*Keep in mind that some of these steps won't be explained properly since this bot is meant for personal use*)

1. **Install Python 3.10 or higher**

    Install Python from https://www.python.org/downloads/

2. **Download the repository**

    | You can either:
    - Install the repo as ZIP then unzip it, or
    - Run ``git clone https://github.com/Kuro-Rui/Fumo-DiscordBot`` on your terminal (which requires you to install `Git <https://git-scm.com/downloads>`_ first)

3. **Make a Virtual Environment (Venv)**

    Run ``python3.10 -m venv .venv`` in the project directory on your terminal (or whatever it's called on your OS)

4. **Activate the Venv**

    Run ``source .venv/bin/activate`` on your terminal

5. **Install the dependencies**

    Make sure you're in your venv, then run these commands on your terminal:

    .. code-block:: bash

        pip install -U pip
        pip install -r requirements.txt

6. **Install Redis**

7. **Start Redis server**

8. **Create Configuration File**

    Create a file named ``config.json`` in the project directory and fill it with the following:

    .. code-block:: json

        {
            "description": "",
            "embed_colour": "",
            "mobile": true,
            "permissions": 0,
            "prefix": "",
            "redis_uri": "",
            "token": ""
        }

    - **description**: The description of the bot. This is used for the bot's help menu.
    - **embed_colour**: The colour of the embeds.
    - **mobile**: Whether the bot will be on mobile status or not.
    - **permissions**: The permissions the bot will have. Use permissions calculator to calculate the value.
    - **prefix**: The prefix the bot will use.
    - **redis_uri**: The URI of the Redis database.
    - **token**: The bot's token.

9. **Run the bot**
    
    Make sure you're on your venv, then run ``python launcher.py`` on your terminal.

----

Credits
-------

- `Cog-Creators <https://github.com/Cog-Creators>`_ for some methods (error handling, rich logging, and pagify) from `Red-DiscordBot <https://github.com/Cog-Creators/Red-DiscordBot>`_
- `Draper <https://github.com/Drapersniper>`_ for the ANSI formatting helper from `PyLav <https://github.com/PyLav/PyLav>`_
- `Danny <https://github.com/Rapptz>`_ for the amazing `discord.py <https://github.com/Rapptz/discord.py>`_ library
- `Glas <https://github.com/DJTOMATO>`_ who helped me making the bot's Imgen cog
- Whoever helped and supported me on Discord which I can't say one by one ❤️
