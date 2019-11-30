import threading


class BufferQueueNode:
    """
    Linked list node of the buffer
    """

    def __init__(self, seq, content):
        self.seq = seq
        self.content = content
        self.next = None
        self.prev = None


class BufferQueue:
    """
    A queue based on linked list with head and tail
    """

    def __init__(self):
        self.head = BufferQueueNode(-1, None)
        self.tail = BufferQueueNode(-1, None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.length = 0
        self.lock = threading.Lock()

    def put(self, seq, content):
        """
        Put a node (seq, content) into the buffer, at the proper position
        :param seq: the seq number
        :param content: content of the buffer
        """
        node = BufferQueueNode(seq, content)
        self.lock.acquire()
        p = self.searchFromBack(seq)
        q = p.next
        p.next = node
        node.next = q
        q.prev = node
        node.prev = p
        self.length += 1
        self.lock.release()

    def get(self):
        """
        Get the first element of the buffer
        """
        self.lock.acquire()
        if self.length == 0:
            self.lock.release()
            return -1, None
        p = self.head.next
        self.head.next = p.next
        p.next.prev = self.head
        self.length -= 1
        self.lock.release()
        return p.seq, p.content

    def searchFromBack(self, seq):
        """
        Find first node such that node.seq <= seq
        """
        node = self.tail.prev
        while True:
            if node.seq <= seq:
                break
            node = node.prev
        return node

    def clear(self):
        """
        Clear the buffer
        :return:
        """
        self.lock.acquire()
        self.head.next = self.tail
        self.tail.prev = self.head
        self.length = 0
        self.lock.release()


if __name__ == '__main__':
    def test():
        buffer = BufferQueue()
        buffer.put(0, 0)
        buffer.put(1, 1)
        buffer.put(3, 3)
        buffer.put(2, 2)
        buffer.put(4, 4)
        for _ in range(6):
            print(buffer.get())
            print(buffer.length)


    test()
