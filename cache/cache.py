import json

class Cache:
    def get(self, key):
        d = self._read()
        if key in d.keys():
            return d[key], True     
        return None, False
    
    def set(self, key, val):
        d = self._read()
        d[key] = val
        self._save(d)

    def _read(self):
        with open('cache.json') as file:
            return json.load(file)
        
    def _save(self, data):
        with open('cache.json', 'w') as file:
            json.dump(data, file)

 
