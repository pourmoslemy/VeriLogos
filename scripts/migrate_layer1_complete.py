from pathlib import Path


SCL_FILE = Path("verilogos/core/operators/sclogic_ops.py")
INIT_FILE = Path("verilogos/core/operators/__init__.py")

SCL_CONTENT = '''from verilogos.core.topology.complexes.subcomplex import Subcomplex
from typing import Tuple


class SCLogicOperations:
    def conjunction(self, p: Subcomplex, q: Subcomplex) -> Subcomplex:
        """Set intersection of simplices: p ∩ q."""
        result = {}
        for dim in set(p.simplices) | set(q.simplices):
            inter = p.simplices.get(dim, set()) & q.simplices.get(dim, set())
            if inter:
                result[dim] = inter
        return Subcomplex(simplices=result, ambient=p.ambient or q.ambient)

    def disjunction(self, p: Subcomplex, q: Subcomplex) -> Subcomplex:
        """Set union of simplices: p ∪ q."""
        result = {}
        for dim in set(p.simplices) | set(q.simplices):
            union = p.simplices.get(dim, set()) | q.simplices.get(dim, set())
            if union:
                result[dim] = union
        return Subcomplex(simplices=result, ambient=p.ambient or q.ambient)

    def negation(self, p: Subcomplex) -> Subcomplex:
        """Complement relative to parent complex: parent.simplices - p.simplices."""
        parent = p.ambient
        if parent is None or not hasattr(parent, "simplices"):
            raise ValueError("Subcomplex must have ambient parent with simplices")
        result = {}
        for dim in set(parent.simplices) | set(p.simplices):
            diff = parent.simplices.get(dim, set()) - p.simplices.get(dim, set())
            if diff:
                result[dim] = diff
        return Subcomplex(simplices=result, ambient=parent)

    def implication(self, p: Subcomplex, q: Subcomplex) -> Subcomplex:
        """Material implication: ¬p ∨ q = disjunction(negation(p), q)."""
        return self.disjunction(self.negation(p), q)

    def necessity(self, p: Subcomplex, sigma: Tuple[int, ...]) -> bool:
        """σ necessarily satisfies p iff ALL faces of σ are in p."""
        dim = len(sigma) - 1
        if dim == 0:
            return sigma in p.simplices.get(0, set())
        faces = self._faces(sigma)
        face_dim = dim - 1
        p_faces = p.simplices.get(face_dim, set())
        return all(face in p_faces for face in faces)

    def possibility(self, p: Subcomplex, sigma: Tuple[int, ...]) -> bool:
        """σ possibly satisfies p iff σ ∈ p OR any face of σ ∈ p."""
        dim = len(sigma) - 1
        if sigma in p.simplices.get(dim, set()):
            return True
        if dim == 0:
            return False
        faces = self._faces(sigma)
        face_dim = dim - 1
        p_faces = p.simplices.get(face_dim, set())
        return any(face in p_faces for face in faces)

    def query(self, p: Subcomplex, sigma: Tuple[int, ...]) -> str:
        """Return one of: explicit, inferable, not_entailed."""
        dim = len(sigma) - 1
        if sigma in p.simplices.get(dim, set()):
            return "explicit"
        if self.necessity(p, sigma):
            return "inferable"
        return "not_entailed"

    def _faces(self, sigma: Tuple[int, ...]) -> list[Tuple[int, ...]]:
        """Return all (k-1)-faces of k-simplex sigma."""
        if len(sigma) <= 1:
            return []
        return [
            tuple(sigma[j] for j in range(len(sigma)) if j != i)
            for i in range(len(sigma))
        ]


__all__ = ["SCLogicOperations"]
'''

INIT_CONTENT = '''from .sclogic_ops import SCLogicOperations

__all__ = ["SCLogicOperations"]
'''


def main() -> None:
    SCL_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCL_FILE.write_text(SCL_CONTENT, encoding="utf-8")
    INIT_FILE.write_text(INIT_CONTENT, encoding="utf-8")
    print("Layer 1 complete migration installed.")


if __name__ == "__main__":
    main()
