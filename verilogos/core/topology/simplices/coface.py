from .face import Face

class Coface:
    def __init__(self, face, simplex):
        self.face = face if isinstance(face, Face) else Face(face)
        self.simplex = simplex
    
    def __hash__(self):
        return hash((self.face, id(self.simplex)))
    
    def __eq__(self, other):
        return (isinstance(other, Coface) and 
                self.face == other.face and 
                self.simplex == other.simplex)


# ── Auto-added missing functions ──────────────

def cofaces(simplex, complex_obj):
    """
    Return all cofaces of a simplex within a simplicial complex.
    A coface of sigma is any simplex tau such that sigma is a face of tau.
    """
    sigma = frozenset(simplex) if not isinstance(simplex, frozenset) else simplex
    result = []
    all_simplices = getattr(complex_obj, 'simplices', [])
    for tau in all_simplices:
        tau_set = frozenset(tau) if not isinstance(tau, frozenset) else tau
        if sigma < tau_set:  # proper subset => sigma is a face of tau
            result.append(tau)
    return result


def minimal_cofaces(simplex, complex_obj):
    """
    Return only the minimal (immediate) cofaces of a simplex.
    These are cofaces whose dimension is exactly dim(simplex) + 1.
    """
    sigma = frozenset(simplex) if not isinstance(simplex, frozenset) else simplex
    target_dim = len(sigma)  # coface dim = len(sigma) + 1 vertices
    result = []
    all_simplices = getattr(complex_obj, 'simplices', [])
    for tau in all_simplices:
        tau_set = frozenset(tau) if not isinstance(tau, frozenset) else tau
        if sigma < tau_set and len(tau_set) == target_dim + 1:
            result.append(tau)
    return result
