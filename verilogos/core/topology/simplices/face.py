class Face:
    def __init__(self, vertices):
        self.vertices = frozenset(vertices)
        self.dim = len(vertices) - 1
    
    def __hash__(self):
        return hash(self.vertices)
    
    def __eq__(self, other):
        return isinstance(other, Face) and self.vertices == other.vertices
