class Node:
    def __init__(self, name, marketplace_url=None, parent=None, db_id=None):
        self.name = name.lower().strip(' ').strip('\n')

        url_end = marketplace_url.find('?')
        if url_end != -1:
            self.marketplace_url = marketplace_url[:url_end]
        else:
            self.marketplace_url = marketplace_url

        self.descendants = []
        self.db_id = db_id
        self.parent = parent

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name
