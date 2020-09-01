import os
import time
import importlib

import dsu

MODULE = 'app'
FILE = f'{MODULE}.py'

if __name__ == "__main__":

    # Start the deployed application
    module = importlib.import_module(MODULE)
    timestamp = os.stat(FILE).st_mtime
    app = module.Main()

    try:
        app.start()

        # Periodically check for updates
        while True: 
            stamp = os.stat(FILE).st_mtime
            if stamp == timestamp:
                time.sleep(3)
            else:
                timestamp = stamp

                # Update the application
                importlib.reload(module) 
                app.update(module.Main())
    except KeyboardInterrupt:
        pass