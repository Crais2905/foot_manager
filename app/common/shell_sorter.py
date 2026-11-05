from collections.abc import Callable
from typing import Any, Protocol, TypeVar

class Comparable(Protocol):
    def __lt__(self, other: Any, /) -> bool: ...


T = TypeVar("T")
K = TypeVar("K", bound=Comparable)


class ShellSorter:
    @staticmethod
    def sort(items: list[T], key: Callable[[T], K]) -> list[T]:
        result = items.copy()
        gap = len(result) // 2

        while gap > 0:
            for index in range(gap, len(result)):
                current = result[index]
                previous = index

                while previous >= gap and key(result[previous - gap]) > key(current):
                    result[previous] = result[previous - gap]
                    previous -= gap

                result[previous] = current
            gap //= 2

        return result
