class Node:
    def __init__(self, name, mp_id=None, db_id=None):
        self.name = name
        self.mp_id = mp_id
        self.db_id = db_id
        self.descendants = []
        self.root = None


def check_if_identical(descedants_1, descedants_2):
    pass


class IdenticalTrees:
    def __init__(self):
        self.root = None

    @staticmethod
    def areIdenticalTrees(root1, root2):
        # Checks if both the trees are empty
        if (root1 == None and root2 == None):
            return True
            # Trees are not identical if root of only one tree is null thus, return false
        if (root1 == None and root2 == None):
            return True
            # If both trees are not empty, check whether the data of the nodes is equal
        # Repeat the steps for left subtree and right subtree
        if (root1 != None and root2 != None):
            return ((root1.data == root2.data) and
                    (IdenticalTrees.areIdenticalTrees(root1.left, root2.left)) and
                    (IdenticalTrees.areIdenticalTrees(root1.right, root2.right)))
        return False