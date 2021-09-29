from tgtg import TgtgClient
from time import sleep
import sys
import logging as log
from os import path
from notifiers import Notifiers
from models import Item, Config, ConfigurationError, TGTGConfigurationError

version = "1.2.2"
prog_folder = path.dirname(sys.executable) if getattr(
    sys, '_MEIPASS', False) else path.dirname(path.abspath(__file__))
config_file = path.join(prog_folder, 'config.ini')
log_file = path.join(prog_folder, 'scanner.log')
log.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=log.INFO,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        log.FileHandler(log_file, mode="w"),
        log.StreamHandler()
    ])


class Scanner():
    def __init__(self):
        self.config = Config(config_file) if path.isfile(
            config_file) else Config()
        if self.config.debug:
            loggers = [log.getLogger(name)
                       for name in log.root.manager.loggerDict]
            for logger in loggers:
                logger.setLevel(log.DEBUG)
            log.info("Debugging mode enabled")
        self.item_ids = self.config.item_ids
        self.amounts = {}
        try:
            self.tgtg_client = TgtgClient(
                email=self.config.tgtg["username"],
                password=self.config.tgtg["password"],
                timeout=60)
            self.tgtg_client._login()
        except:
            raise TGTGConfigurationError()
        self.notifiers = Notifiers(self.config)

    def _job(self):
        for item_id in self.item_ids:
            try:
                if item_id != "":
                    data = self.tgtg_client.get_item(item_id)
                    self._check_item(Item(data))
            except:
                log.error(
                    "itemId {0} - Error! - {1}".format(item_id, sys.exc_info()))
        for data in self._get_favorites():
            try:
                self._check_item(Item(data))
            except:
                log.error("checkItem Error! - {0}".format(sys.exc_info()))
        log.debug("new State: {0}".format(self.amounts))

    def _get_favorites(self):
        items = []
        page = 1
        page_size = 100
        error_count = 0
        while True and error_count < 5:
            try:
                new_items = self.tgtg_client.get_items(
                    favorites_only=True,
                    page_size=page_size,
                    page=page
                )
                items += new_items
                if len(new_items) < page_size:
                    break
                page += 1
            except:
                log.error("getItem Error! - {0}".format(sys.exc_info()))
                error_count += 1
        return items

    def _check_item(self, item: Item):
        try:
            if self.amounts[item.id] == 0 and item.items_available > self.amounts[item.id]:
                self._send_messages(item)
        except:
            self.amounts[item.id] = item.items_available
        finally:
            if self.amounts[item.id] != item.items_available:
                log.info(
                    "{0} - New amount: {1}".format(item.display_name, item.items_available))
                self.amounts[item.id] = item.items_available

    def _send_messages(self, item: Item):
        log.info(
            "Sending {0} - new Amount {1}".format(item.display_name, item.items_available))
        self.notifiers.send(item)

    def run(self):
        log.info("Scanner started ...")
        while True:
            try:
                self._job()
            except:
                log.error("Job Error! - {0}".format(sys.exc_info()))
            finally:
                sleep(self.config.sleep_time)


def welcome_message():
    log.info("  ____  ___  ____  ___    ____   ___   __   __ _  __ _  ____  ____  ")
    log.info(
        " (_  _)/ __)(_  _)/ __)  / ___) / __) / _\ (  ( \(  ( \(  __)(  _ \ ")
    log.info(
        "   )( ( (_ \  )( ( (_ \  \___ \( (__ /    \/    //    / ) _)  )   / ")
    log.info("  (__) \___/ (__) \___/  (____/ \___)\_/\_/\_)__)\_)__)(____)(__\_) ")
    log.info("")
    log.info(f"Version {version}")
    log.info("©2021, Henning Merklinger")
    log.info(
        "For documentation and support please visit https://github.com/Der-Henning/tgtg")
    log.info("")


def main():
    try:
        welcome_message()
        scanner = Scanner()
        scanner.run()
    except ConfigurationError as err:
        log.error("Configuration Error - {0}".format(err))
    except KeyboardInterrupt:
        log.info("Shutting down scanner ...")
    except:
        log.error("Unexpected Error! - {0}".format(sys.exc_info()))


if __name__ == "__main__":
    main()
