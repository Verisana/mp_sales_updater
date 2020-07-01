class Node:
    def __init__(self, name, mp_url=None, parent=None, db_id=None):
        self.name = name.lower().strip(' ').strip('\n')
        self.mp_url = mp_url
        self.descendants = []
        self.db_id = db_id
        self.parent = parent

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
