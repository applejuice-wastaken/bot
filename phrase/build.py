import abc

from phrase.pronouns import Pronoun, figure_pronouns, collective
from phrase import pronouns
from util.human_join_list import human_join_list

class _Fragment(abc.ABC):
    """Base class that allows addition for more straightforward templating"""
    @classmethod
    def _compute_add(cls, this, other):
        if not isinstance(this, _FragmentList):
            this = [this]

        if not isinstance(other, _FragmentList):
            other = [other]

        return _FragmentList([*this, *other])

    def __add__(self, other):
        return self._compute_add(self, other)

    def __radd__(self, other):
        return self._compute_add(other, self)

class _FragmentList(_Fragment, list):
    pass

class _Resolvable(abc.ABC):
    """Base class that resolves self to a string or another resolvable"""

    @abc.abstractmethod
    async def resolve(self, referenced, speaker, author, **replace):
        pass


class _DeferredReferenceMorpheme(_Fragment, _Resolvable):
    def __init__(self, deferred_reference, morpheme):
        self.deferred_reference = deferred_reference
        self.morpheme = morpheme

    async def resolve(self, referenced, speaker, author, **replace):
        if self.deferred_reference.identifier in replace:
            reference = Reference(replace[self.deferred_reference.identifier])
            return _ReferenceMorpheme(reference, self.morpheme)

        else:
            raise RuntimeError(f"{self.deferred_reference.identifier} has no replacement")


class DeferredReference(_Fragment, _Resolvable):
    def __init__(self, identifier):
        self.identifier = identifier

    async def resolve(self, referenced, speaker, author, **replace):
        if self.identifier in replace:
            return Reference(replace[self.identifier])

        else:
            raise RuntimeError(f"{self.identifier} has no replacement")

    def __getattr__(self, item):
        return _DeferredReferenceMorpheme(self, item)


class _ReferenceMorpheme(_Fragment, _Resolvable):
    def __init__(self, reference, morpheme):
        self.reference = reference
        self.morpheme = morpheme

    async def resolve(self, referenced, speaker, author, **replace):
        list_baking = []

        if self.reference.collective and self.reference.users in referenced:
            morpheme = self.morpheme

            if author is not None and author == self.reference.users and morpheme == "object":
                morpheme = "reflexive"

            pronoun = pronouns.collective
            if speaker is not None and all(s in self.reference.users for s in speaker):
                pronoun = pronouns.self_collective

            list_baking.append(getattr(pronoun, morpheme))
        else:
            for user in self.reference.users:
                if speaker is not None and len(speaker) == 1 and speaker[0] == user:
                    pronoun = pronouns.self

                elif user in referenced:
                    pronoun = await figure_pronouns(user)

                else:
                    pronoun = Pronoun.pronounless(user)
                    referenced.append(user)

                morpheme = self.morpheme

                if author is not None and len(author) == 1 and author[0] == user and morpheme == "object":
                    morpheme = "reflexive"

                list_baking.append(getattr(pronoun, morpheme))

            if self.reference.collective:
                referenced.append(self.reference.users)

        return human_join_list(list_baking)

class Reference(_Fragment, _Resolvable):
    what = _ReferenceMorpheme

    def __init__(self, users: list):
        if not isinstance(users, list):
            users = [users]

        if len(users) == 0:
            raise ValueError("Empty reference")

        self.users = users
        self.collective = len(users) > 1

    def __getattr__(self, item):
        return _ReferenceMorpheme(self, item)

    async def resolve(self, referenced, speaker, author, **replace):
        return self.subject


class MaybeReflexive(_Fragment, _Resolvable):
    def __init__(self, author, target):
        self.author = author
        self.target = target

    async def resolve(self, referenced, speaker, author, **replace):
        author = self.author
        target = self.target

        while not isinstance(author, (Reference, _ReferenceMorpheme)):
            author = await author.resolve(referenced, speaker, author, **replace)

        while not isinstance(target, (Reference, _ReferenceMorpheme)):
            target = await target.resolve(referenced, speaker, author, **replace)

        if isinstance(author, _ReferenceMorpheme):
            author = author.reference

        if isinstance(target, _ReferenceMorpheme):
            target = target.reference

        return await target.object.resolve(referenced, speaker, author.users, **replace)

async def build(fragments: list, *, speaker=None, author=None, **replace):
    ret = []
    referenced = []

    for fragment in fragments:
        while isinstance(fragment, _Resolvable):
            fragment = await fragment.resolve(referenced, speaker, author, **replace)

        if isinstance(fragment, str):
            ret.append(fragment)

        else:
            raise RuntimeError(f"Bad Resolve: {type(fragment)}")

    return " ".join(ret)
