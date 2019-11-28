import threading


class BufferQueueNode:
    def __init__(self, seq, content):
        self.seq = seq
        self.content = content
        self.next = None
        self.prev = None


class BufferQueue:
    def __init__(self):
        self.head = BufferQueueNode(-1, None)
        self.tail = BufferQueueNode(-1, None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self.length = 0
        self.lock = threading.Lock()

    def put(self, seq, content):
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
        self.lock.acquire()
        if self.length == 0:
            self.lock.release()
            return None
        p = self.head.next
        self.head.next = p.next
        p.next.prev = self.head
        self.length -= 1
        self.lock.release()
        return p.content

    def searchFromBack(self, seq):
        # Find first node s.t. node.seq <= seq
        node = self.tail.prev
        while True:
            if node.seq <= seq:
                break
            node = node.prev
        return node


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
