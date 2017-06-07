from __future__ import absolute_import

from collections import namedtuple

Path = namedtuple('Path', 'l, r, pnodes, ppath, changed')


def zipper(root, is_branch, children, make_node):
    return Loc(root, None, is_branch, children, make_node)


_Loc = namedtuple(
    'Loc',
    ['current', 'path', 'is_branch', 'get_children', 'make_node'],
)


class Loc(_Loc):

    def node(self):
        return self.current

    def children(self):
        if self.branch():
            return self.get_children(self.current)

    def branch(self):
        return self.is_branch(self.current)

    def at_end(self):
        return not bool(self.path)

    def down(self):
        children = self.children()
        if children:
            extra = (self.current,)
            pnodes = self.path.pnodes + extra if self.path else extra
            path = Path(
                l=(),
                r=children[1:],
                pnodes=pnodes,
                ppath=self.path,
                changed=False,
            )

            return self._replace(current=children[0], path=path)

    def up(self):
        if self.path:
            l, r, pnodes, ppath, changed = self.path
            if pnodes:
                pnode = pnodes[-1]
                if changed:
                    return self._replace(
                        current=self.make_node(pnode, l + (self.current,) + r),
                        path=ppath and ppath._replace(changed=True),
                    )
                else:
                    return self._replace(current=pnode, path=ppath)

    def top(self):
        loc = self
        while loc.path:
            loc = loc.up()
        return loc

    def right(self):
        if self.path and self.path.r:
            l, rs = self.path[:2]
            current, rnext = rs[0], rs[1:]
            return self._replace(current=current, path=self.path._replace(
                l=l + (self.current,),
                r=rnext,
            ))

    def leftmost_descendant(self):
        loc = self
        while loc.branch():
            d = loc.down()
            if d:
                loc = d
            else:
                break

        return loc

    def _rightmost(self):
        """Returns the right most sibling at this location or self"""

        path = self.path
        if path:
            l, r = self.path[:2]
            t = l + (self.current,) + r
            current = t[-1]

            return self._replace(current=current, path=path._replace(
                l=t[:-1],
                r=(),
            ))
        else:
            return self

    def _rightmost_descendant(self):
        loc = self
        while loc.branch():
            d = loc.down()
            if d:
                loc = d._rightmost()
            else:
                break
        return loc

    def postorder_next(self):
        """
        Visit's nodes in depth-first post-order.

        For eaxmple given the following tree:

                        a
                    /     \
                 b         e
                 ^         ^
                c d     f g

        postorder next will visit the nodes in the following order
        c, d, b, f, g, e a


        Note this method ends when it reaches the root node. To
        start traversal from the root call leftmost_descendant()
        first. See postorder_iter for an example.

        """

        r = self.right()
        if (r):
            return r.leftmost_descendant()
        else:
            return self.up()

    def edit(self, f, *args):
        """Replace the node at this loc with the value of f(node, *args)"""
        return self.replace(f(self.current, *args))

    def insert(self, item):
        """
        Inserts the item as the leftmost child of the node at this loc,
        without moving.
        """
        return self.replace(
            self.make_node(self.node(), (item,) + self.children()),
        )

    def replace(self, value):
        if self.path:
            return self._replace(
                current=value,
                path=self.path._replace(changed=True),
            )
        else:
            return self._replace(current=value)

    def find(self, func):
        loc = self.leftmost_descendant()
        while True:
            if func(loc):
                return loc
            elif loc.at_end():
                return None
            else:
                loc = loc.postorder_next()

    def remove(self):
        """
        Removes the node at the current location, returning the
        node that would have proceeded it in a depth-first walk.

        For eaxmple given the following tree:

                        a
                    /     \
                 b         e
                 ^         ^
                c d     f g
                ^
            c1 c2
        Removing c would return b, removing d would return c2.


        """
        path = self.path
        if not path:
            raise IndexError('Remove at top')

        l, r, pnodes, ppath, changed = path

        if l:
            ls, current = l[:-1], l[-1]
            return self._replace(current=current, path=path._replace(
                l=ls,
                changed=True,
            ))._rightmost_descendant()

        else:
            return self._replace(
                current=self.make_node(pnodes[-1], r),
                path=ppath and ppath._replace(changed=True),
            )


del _Loc
