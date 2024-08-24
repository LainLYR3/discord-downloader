import os
import shutil
import datetime
import discord
import logging

from discord_downloader.config import cfg
from discord_downloader.parser import base_parser
from discord_downloader.utils import (
    none_or_int,
    none_or_str,
    none_or_date,
    none_or_list,
)

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class MyClient(discord.Client):
    async def on_ready(self):
        logging.info(f'Logged on as {self.user}')

    async def on_message(self, message):
        if message.author == self.user:
            return

        if message.content == 'ping':
            await message.channel.send('pong')


def main(
    client,
    token,
    filetypes=none_or_str(cfg.get("args", "filetypes")),
    output_dir=str(cfg.get("args", "output_dir")),
    channels=none_or_list(cfg.get("args", "channels")),
    server=none_or_str(cfg.get("args", "server")),
    dry_run=cfg.getboolean("args", "dry_run"),
    num_messages=none_or_int(cfg.get("args", "num_messages")),
    verbose=cfg.getboolean("args", "verbose"),
    prepend_user=cfg.getboolean("args", "prepend_user"),
    after=none_or_date(cfg.get("args", "after")),
    before=none_or_date(cfg.get("args", "before")),
    zipped=cfg.getboolean("args", "zipped"),
    include_str=none_or_str(cfg.get("args", "include_str")),
    exclude_str=none_or_str(cfg.get("args", "exclude_str")),
):
    download_dir = "discord_downloads_" + datetime.datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join(output_dir, download_dir)
    os.makedirs(output_dir, exist_ok=True)

    @client.event
    async def on_ready(
        server=server,
        channels=channels,
        num_messages=num_messages,
        filetypes=filetypes,
        verbose=verbose,
        output_dir=output_dir,
        prepend_user=prepend_user,
        dry_run=dry_run,
        after=after,
        before=before,
        include_str=include_str,
        exclude_str=exclude_str,
    ):
        if server is None:
            server = client.guilds[0].name
        
        if (after is not None and before is not None) or (num_messages is None or num_messages <= 0):
            num_messages = None

        num_str = str(num_messages) if num_messages is not None else "inf"

        app_info = await client.application_info()
        total = 0 
        for g in client.guilds:
            if g.name == server:
                logging.info(f"Connected to {g.name} as {client.user}, slave of {app_info.owner.name}")
    
                text_channels = g.text_channels
                for c in text_channels:
                    if channels is None or c.name in channels:
                        count = 0
                        logging.info(f"Searching in channel: {c.name}")
                        
                        try:
                            async for m in c.history(limit=num_messages, after=after, before=before):
                                logging.debug(f"Processing message: {m.id}")
                                for a in m.attachments:
                                    logging.debug(f"Found attachment: {a.filename}")
                                    
                                    if (filetypes is None or a.filename.split(".")[-1] in filetypes) and \
                                       (include_str is None or include_str in a.filename) and \
                                       (exclude_str is None or exclude_str not in a.filename):
                                        
                                        star_count = 0
                                        for r in m.reactions:
                                            if str(r.emoji) == '⭐':
                                                star_count = r.count
                                                break
                                        logging.debug(f"Attachment {a.filename} has {star_count} star reactions")
                                        
                                        if star_count >= 3:
                                            logging.info(f"Found {a.filename} with {star_count} star reactions")
                                            count += 1
                                            fname = m.author.name.replace(" ", "_") + "__" + a.filename if prepend_user else a.filename
                                            fname = os.path.join(output_dir, fname)
                                            if not dry_run:
                                                try:
                                                    await a.save(fname)
                                                    logging.info(f"Successfully saved: {fname}")
                                                except Exception as e:
                                                    logging.error(f"Failed to save {fname}: {str(e)}")
                                        else:
                                            logging.debug(f"Skipped {a.filename} with only {star_count} star reactions")
                                    else:
                                        logging.debug(f"Attachment {a.filename} did not meet filter criteria")
    
                        except discord.errors.Forbidden:
                            logging.error(f"No permission to read history in channel: {c.name}")
                        except Exception as e:
                            logging.error(f"Error processing channel {c.name}: {str(e)}")
    
                        logging.info(f"Found and downloaded {count} files with 3 or more star reactions in {c.name}")
                        total += count
    
            if dry_run:
                logging.info(f"Dry run! 0 of {total} files saved!")
            else:
                logging.info(f"Saved {total} files with 3 or more star reactions to {output_dir}")
        
        await client.close()

    @client.event
    async def on_disconnect(zipped=zipped, dry_run=dry_run, output_dir=output_dir):
        if zipped and not dry_run:
            logging.info("Zipping and cleaning files...")
            shutil.make_archive(output_dir, "zip", output_dir)
            shutil.rmtree(output_dir)

        logging.info("Disconnected from Discord")

    try:
        client.run(token)
    except discord.errors.LoginFailure:
        logging.error("Failed to log in: Invalid token")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    parser = base_parser
    args = parser.parse_args()

    intents = discord.Intents.default()
    intents.message_content = True

    client = discord.Client(intents=intents)

    main(
        client,
        args.token,
        filetypes=args.filetypes,
        output_dir=args.output_dir,
        channels=args.channels,
        server=args.server,
        dry_run=args.dry_run,
        num_messages=args.num_messages,
        verbose=args.verbose,
        prepend_user=args.prepend_user,
        after=args.after,
        before=args.before,
        zipped=args.zipped,
        include_str=args.include_str,
        exclude_str=args.exclude_str,
    )