"""
Recent Files History Manager
Mike Hilton, Eckerd College

The class FileHistoryManager manages a list of recently opened files.
"""

class FileHistoryManager:

    def __init__(self, config, size=10):
        self._config = config       # configparser object used to persist the file history
        self._configSection = 'File_History'     # name of section in config file where file history is stored
        self._history = []          # concrete implementation of history is a queue implemented using a list
        self._size = size           # maximum number of items to keep in history

    def addFile(self, filepath):
        """
        Adds a file to the front of the history.
        Inputs:
            filepath        string; path of file to add
        Returns:
            Nothing
        """
        if filepath in self._history:
            self._history.remove(filepath)
        self._history.insert(0, filepath)
        while len(self._history) > self._size:
            self._history.pop()
        self._writeHistory()

    def clear(self):
        """
        Clears all the items from the history.
        """
        self._history.clear()
        self._writeHistory()

    def deleteFile(self, filepath):
        """
        Deletes a file from the file history.
        Inputs:
            filepath        string; path of file to delete
        Returns:
            Nothing
        """
        if filepath in self._history:
            self._history.remove(filepath)
            self._writeHistory()

    def getConfigSection(self):
        """
        Returns the name of the section of the config file where the file history is stored.
        """
        return self._configSection
        
    def loadHistory(self):
        """
        Loads the file history from the configuration object.
        """
        self._history.clear()
        if self.getConfigSection() in self._config:
            files = self._config[self.getConfigSection()]
            for key in sorted(list(files.keys())):
                if "file" in key:
                    self._history.append(files[key])

    def refreshMenu(self, menu, actionFunction):
        """
        Updates a menu item to contain the current file history.
        Inputs:
            menu    QMenu object to be updated
        Returns:
            Nothing
        """
        menu.clear()
        for item in self._history:
            action = menu.addAction(item)
            # the lambda function is used to pass an additional argument to actionFunction
            # a good explanation of this technique is at https://www.learnpyqt.com/courses/adanced-ui-features/transmitting-extra-data-qt-signals/
            action.triggered.connect(lambda x = True, a=item: actionFunction(x, a))

    def __str__(self):
        """
        Returns a string representation of the file history.
        """
        return str(self._history)

    def updateMenu(self, filepath, menuItem, action):
        self.addFile(filepath)
        self.refreshMenu(menuItem, action)
        self._writeHistory()


    def _writeHistory(self):
        """
        Write the file history to the config object.
        """
        self._config[self.getConfigSection()] = {}
        for i in range(len(self._history)):
            self._config[self.getConfigSection()][f"file{i}"] = self._history[i]


if __name__ == '__main__':
    import configparser
    config = configparser.ConfigParser()  
    history = FileHistoryManager(config)
    # add some items
    history.addFile('a')
    print("addFile('a') =", history)
    history.addFile('b')
    print("addFile('b') =", history)
    history.addFile('a')
    print("addFile('a') =", history)
    history.addFile('c')
    print("addFile('c') =", history)   
    print("config =", list(config[history.getConfigSection()].items()))

    # write out config
    with open('test.config', 'w') as configfile:
        config.write(configfile)      
    
    # delete some items
    history.deleteFile('a')
    print("deleteFile('a') =", history)
    print("config =", list(config[history.getConfigSection()].items()))   
    history.deleteFile('c')     
    print("deleteFile('c') =", history)
    print("config =", list(config[history.getConfigSection()].items()))     

    # load the config back
    config.read('test.config') 
    print("config =", list(config[history.getConfigSection()].items()))         
    history.loadHistory()
    print("history =", history)
