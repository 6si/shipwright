from collections import namedtuple

Path=namedtuple('Path', 'l, r, pnodes, ppath, changed')


def isa(type):
  """
  Returns is_<type>(obj) a function that returns true 
  when it's argument is the istance of type
  """
  def f(obj):
    return isinstance(obj, type)

  f.__name__ = "is_{0}".format(type)
  return f


native_list = __builtins__['list']
def list(root):
  return zipper(
    root,
    isa(native_list), 
    tuple, 
    lambda node, children: native_list(children)
  )


native_dict = __builtins__['dict']
is_dict=isa(native_dict)
def dict(root):
  return zipper(
    root,
    # i is either the root object or a tuple of key value pairs
    lambda i: i is is_dict(root) or is_dict(i[1]), 
    lambda i: tuple(i.items() if i is is_dict(i) else i[1].items()), 
    lambda node, children: native_dict(children)
  )


def zipper(root, is_branch, children, make_node):
  return Loc(root, None, is_branch, children, make_node)
  

class Loc(namedtuple('Loc', 'current, path, is_branch, get_children, make_node')):

  def __repr__(self):
    return "<zipper.Loc({}) object at {}>".format(self.current, id(self))

  ## Context
  def node(self):
    return self.current

  def children(self):
    if self.branch():
      return self.get_children(self.current)

  def branch(self):
    return self.is_branch(self.current)

  def root(self):
    return self.top().current

  def at_end(self):
    return not bool(self.path)

  ## Navigation
  def down(self):
    children = self.children()
    if children:
      path = Path(
        l=(), 
        r=children[1:], 
        pnodes=self.path.pnodes + (self.current,) if self.path else (self.current,),
        ppath = self.path,
        changed=False
      )

      return self._replace(current=children[0],path=path)

  def up(self):
    if self.path:
      l, r, pnodes, ppath, changed = self.path
      if pnodes:
        pnode = pnodes[-1]
        if changed:
          return self._replace(
            current=self.make_node(pnode, l+(self.current,)+r),
            path = ppath and ppath._replace(changed=True)
          )
        else:
          return self._replace(current=pnode,path=ppath)

  def top(self):
    loc = self
    while loc.path:
      loc = loc.up()
    return loc

  def ancestor(self,filter):
    """
    Return the first ancestor preceding the current loc that
    matches the filter(ancestor) function. 

    The filter function is invoked with the location of the
    next ancestor. If the filter function returns true then
    the ancestor will be returned to the invoker of 
    loc.ancestor(filter) method. Otherwise the search will move
    to the next ancestor until the top of the tree is reached.
    """

    u = self.up()
    while u:
      if filter(u):
        return u
      else:
        u = u.up()
            
  def left(self):
    if self.path and self.path.l:
      ls, r = self.path[:2]
      l,current = ls[:-1], ls[-1]
      return self._replace(current=current, path=self.path._replace(
        l = l,
        r = (self.current,) + r
      )) 
  
  def leftmost(self):
    """Returns the left most sibling at this location or self"""

    path = self.path
    if path:
      l,r = self.path[:2]
      t = l + (self.current,) + r
      current = t[0]


      return self._replace(current=current, path=path._replace(
        l = (),
        r = t[1:]
      ))
    else:
      return self

  def rightmost(self):
    """Returns the right most sibling at this location or self"""

    path = self.path
    if path:
      l,r = self.path[:2]
      t = l + (self.current,) + r
      current = t[-1]


      return self._replace(current=current, path=path._replace(
        l = t[:-1],
        r = ()
      ))
    else:
      return self


  def right(self):
    if self.path and self.path.r:
      l, rs = self.path[:2]
      current, rnext = rs[0], rs[1:]
      return self._replace(current=current, path=self.path._replace(
        l=l+(self.current,),
        r = rnext
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

  def rightmost_descendant(self):
    loc = self
    while loc.branch():
      d = loc.down()
      if d:
        loc = d.rightmost()
      else:
        break
    return loc

  def move_to(self, dest):
    """
    Move to the same 'position' in the tree as the given loc and return
    the loc that currently resides there. This method does not gurantee
    that the node from the previous loc will be the same node if the node
    or it's ancestory has bee modified.
    """

    moves = []
    path = dest.path

    while path:
      moves.extend(len(path.l) * ['r'])
      moves.append('d')
      path = path.ppath

    moves.reverse()

    loc = self.top()
    for m in moves:
      if m == 'd':
        loc = loc.down()
      else:
        loc = loc.right()

    return loc



  ## Enumeration
  def preorder_iter(self):
    loc = self
    while loc:
      loc = loc.preorder_next()
      if loc:
        yield loc
     
  def preorder_next(self):
    """
    Visit's nodes in depth-first pre-order. 

    For eaxmple given the following tree:

            a
          /   \
         b     e
         ^     ^
        c d   f g

    preorder_next will visit the nodes in the following order
    b, c, d, e, f, g, a
  
    See preorder_iter for an example.
    """

    if self.path is ():
      return None

    n = self.down() or self.right()
    
    if n is not None:
      return n
    else:
      u = self.up()
      while u:
        r = u.right()
        if r:
          return r
        else:
          if u.path:
            u = u.up()
          else:
            return u._replace(path=())

  
  def postorder_next(self):
    """
    Visit's nodes in depth-first post-order. 

    For eaxmple given the following tree:

            a
          /   \
         b     e
         ^     ^
        c d   f g

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

  def postorder_iter(self):
    loc = self.leftmost_descendant()

    while loc:
      yield loc
      loc = loc.postorder_next()


  ## editing
  def append(self, item):
    """
    Inserts the item as the rightmost child of the node at this loc,
    without moving.
    """
    return self.replace(
      self.make_node(self.node(),  self.children()+(item,))
    )

  def edit(self, f, *args):
    "Replace the node at this loc with the value of f(node, *args)"
    return self.replace(f(self.current, *args))

  def insert(self, item):
    """
    Inserts the item as the leftmost child of the node at this loc,
    without moving.
    """
    return self.replace(
      self.make_node(self.node(), (item,) + self.children())
    )


  def insert_left(self, item):
    """Insert item as left sibling of node without moving"""
    path = self.path
    if not path:
      raise IndexError("Can't insert at top")

    new = path._replace(l=path.l + (item,) , changed=True)
    return self._replace(path=new)
 

  def insert_right(self, item):
    """Insert item as right sibling of node without moving"""
    path = self.path
    if not path:
      raise IndexError("Can't insert at top")

    new = path._replace(r=(item,) + path.r, changed=True)
    return self._replace(path=new)
  
  def replace(self, value):
    if self.path:
      return self._replace(current=value, path=self.path._replace(changed=True))
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
          /   \
         b     e
         ^     ^
        c d   f g
        ^
      c1 c2
    Removing c would return b, removing d would return c2.


    """
    path = self.path
    if not path:
      raise IndexError("Remove at top")

    l, r, pnodes, ppath, changed = path

    if l:
      ls, current = l[:-1], l[-1]
      return self._replace(current=current, path=path._replace(
        l=ls,
        changed=True
      )).rightmost_descendant()

    else:
      return self._replace(
        current=self.make_node(pnodes[-1], r),
        path = ppath and ppath._replace(changed=True)
      )



