import threading
import time
import hashlib
import random
from queue import Queue

class Transaction:
    def __init__(self, transaction_id, size):
        self.transaction_id = transaction_id
        self.size = size

class Block:
    def __init__(self, index, miner_id, previous_hash, timestamp, block_generation_time, transactions, hash, nonce):
        self.index = index
        self.miner_id =miner_id
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.block_generation_time = block_generation_time
        self.transactions = transactions
        self.hash = hash
        self.nonce = nonce

class Blockchain:
    def __init__(self, difficulty):
        self.chain = [self.create_genesis_block()]
        self.difficulty = difficulty
        self.chain_lock = threading.Lock()
        self.print_lock = threading.Lock()

    def create_genesis_block(self):
        return Block(0, 0, "0", time.time(), 0, [], self.calculate_hash(0, "0", time.time(), [], 0), 0)
    
    def calculate_hash(self, index, previous_hash, timestamp, transactions, nonce):
        value = f"{index}{previous_hash}{timestamp}{transactions}{nonce}"
        return hashlib.sha256(value.encode('utf-8')).hexdigest()

    def get_latest_block(self):
        with self.chain_lock:  
            return self.chain[-1]
    
    def add_block(self, block):
        with self.chain_lock:
            self.chain.append(block)
    
    def print_message(self, message):
        with self.print_lock:
            print(message)

class Node:
    def __init__(self, node_id, blockchain, network_queues, network_stand_down_event, network_penalty_event, max_blocks, stop_event):
        self.node_id = node_id
        self.blockchain = blockchain
        self.network_queues = network_queues
        self.network_stand_down_event = network_stand_down_event
        self.network_penalty_event = network_penalty_event
        self.local_queue = Queue()
        self.max_blocks = max_blocks
        self.stop_event = stop_event
        self.penalty_event = threading.Event()
        self.penalty_time = 1000
        self.stand_down_event = threading.Event()
        self.block_verification_time = 10
        self.bvt_start_time = None
        self.pending_blocks = []
        self.verified_blocks = []

    def generate_transactions(self):
        num_transactions = random.randint(1, 10)
        transactions = []
        for i in range(num_transactions):
            transaction_id = f"tx_{random.randint(1000, 9999)}"
            size = random.randint(100, 1000)
            transactions.append(Transaction(transaction_id, size))
        return transactions
    
    def mine_block(self):
        while not self.stop_event.is_set():
            if self.penalty_event.is_set():
                self.blockchain.print_message(f"Node {self.node_id} starts penalty!")
                self.handle_penalty()
                self.blockchain.print_message(f"Node {self.node_id} ends penalty")

            if self.stand_down_event.is_set():
                continue     
            
            # # Test case of 51% attack simulation
            # if self.node_id == 3:
            #     previous_block = self.blockchain.get_latest_block()
            #     index = previous_block.index + 1
            #     miner_id = self.node_id
            #     previous_hash = previous_block.hash
            #     nonce = 0
            #     transactions = self.generate_transactions()
            #     timestamp = time.time()
            #     mining_start_time = time.time()  # Record the mining start time
            #     block_1_hash = self.blockchain.calculate_hash(index, previous_hash, timestamp, transactions, nonce)
            #     block_2_hash = self.blockchain.calculate_hash(index + 1, block_1_hash, timestamp, transactions, nonce)
            #     block_3_hash = self.blockchain.calculate_hash(index + 2, block_2_hash, timestamp, transactions, nonce)
                
            #     if self.stop_event.is_set() or self.stand_down_event.is_set() or self.penalty_event.is_set():
            #         continue

            #     block_1 = Block(index, miner_id, previous_hash, timestamp, 0, transactions, block_1_hash, nonce)
            #     block_2 = Block(index + 1, miner_id, block_1_hash, timestamp, 0, transactions, block_2_hash, nonce)
            #     block_3 = Block(index + 2, miner_id, block_2_hash, timestamp, 0, transactions, block_3_hash, nonce)

            #     self.blockchain.print_message(f"\033[34mThe Attacker (Node {self.node_id}) mines a new block: {block_1.hash}\033[0m")
            #     self.blockchain.print_message(f"\033[34mThe Attacker (Node {self.node_id}) mines a new block: {block_2.hash}\033[0m")
            #     self.blockchain.print_message(f"\033[34mThe Attacker (Node {self.node_id}) mines a new block: {block_3.hash}\033[0m")

            #     self.broadcast_block(block_1, mining_start_time)
            #     self.broadcast_block(block_2, mining_start_time)
            #     self.broadcast_block(block_3, mining_start_time)
            #     time.sleep(5) # sleep the thread to ensure node 3 won't mine a block anymore before entering SD
            #     continue

            time.sleep(random.uniform(1, 5))  # Simulate time delay for each nodes
            previous_block = self.blockchain.get_latest_block()
            index = previous_block.index + 1
            miner_id = self.node_id
            previous_hash = previous_block.hash
            nonce = 0
            transactions = self.generate_transactions()
            timestamp = time.time()
            mining_start_time = time.time()  # Record the mining start time
            hash = self.blockchain.calculate_hash(index, previous_hash, timestamp, transactions, nonce)

            # Find correct hash matches the target
            while not hash.startswith('0' * self.blockchain.difficulty) and not self.stop_event.is_set():
                nonce += 1
                timestamp = time.time()
                hash = self.blockchain.calculate_hash(index, previous_hash, timestamp, transactions, nonce)
            
            if self.stop_event.is_set() or self.stand_down_event.is_set() or self.penalty_event.is_set():
                continue

            new_block = Block(index, miner_id, previous_hash, timestamp, 0, transactions, hash, nonce)

            tx_size_str = ""
            for tx in new_block.transactions:
                tx_size_str += "{" + str(tx.size) + "}"
            self.blockchain.print_message(f"\033[34mNode {self.node_id} mines a new block: {new_block.hash} with transactions size: {tx_size_str}\033[0m")

            self.broadcast_block(new_block, mining_start_time)

            if len(self.blockchain.chain) >= self.max_blocks:
                self.stop_event.set()
        
    def broadcast_block(self, block, mining_start_time):
        block_generation_time = time.time() - mining_start_time  # Calculate the block generation time
        block.block_generation_time = block_generation_time
        for queue in self.network_queues:
            queue.put(block)

    def receive_block(self):
        while not self.stop_event.is_set():
            block = self.local_queue.get()
            if self.penalty_event.is_set():
                continue

            self.blockchain.print_message(f"Node {self.node_id} receives block: {block.hash}")
            if not self.stand_down_event.is_set():
                self.pending_blocks.clear()
                self.verified_blocks.clear()
                self.pending_blocks.append(block)
                self.stand_down_event.set()
                self.bvt_start_time = time.time()
                self.blockchain.print_message(f"Node {self.node_id} starts Stand Down process with block: {block.hash}")
            elif self.stand_down_event.is_set():
                self.pending_blocks.append(block)

            if len(self.blockchain.chain) >= self.max_blocks:
                self.stop_event.set()

    def stand_down(self):
        while not self.stop_event.is_set():
            if self.stand_down_event.is_set():
                if (time.time() - self.bvt_start_time) > self.block_verification_time:  # BVT over
                    if len(self.verified_blocks) == 1:
                        if (self.blockchain.get_latest_block().index + 1 == self.verified_blocks[0].index):
                            self.blockchain.add_block(self.verified_blocks[0])
                            self.blockchain.print_message(f"\033[1;33mNode {self.node_id} adds block: {self.verified_blocks[0].hash} to chain\033[0m")
                    elif len(self.verified_blocks) > 1:
                        selected_block = self.prioritiztion_block()
                        if (self.blockchain.get_latest_block().index + 1 == selected_block.index):
                            self.blockchain.add_block(selected_block)
                            self.blockchain.print_message(f"\033[1;33mNode {self.node_id} adds block: {selected_block.hash} to chain\033[0m")

                    
                    self.stand_down_event.clear()
                    self.pending_blocks.clear()
                    self.verified_blocks.clear()
                    self.blockchain.print_message(f"Node {self.node_id} ends Stand Down process")
                    continue

                for pending_block in self.pending_blocks:
                    if self.verification_block(pending_block, self.blockchain.get_latest_block()):
                        self.verified_blocks.append(pending_block)
                        self.pending_blocks.remove(pending_block)
                        self.blockchain.print_message(f"\033[32mblock: {pending_block.hash} passes verification by Node {self.node_id}\033[0m")
                    else:
                        self.pending_blocks.remove(pending_block)
                        self.blockchain.print_message(f"\033[31mblock: {pending_block.hash} fails verification by Node {self.node_id}\033[0m")
                        if not self.network_penalty_event[pending_block.miner_id - 1].is_set():
                            self.network_penalty_event[pending_block.miner_id - 1].set()  # impose penalty to miner
                        break

    def prioritiztion_block(self):
        max_point = 0

        # Sort transactions of each block in descending order
        for block in self.verified_blocks:
            block.transactions.sort(key=lambda tx: tx.size, reverse=True)

        # Find the least number of transactions any block has
        min_transactions = min(len(block.transactions) for block in self.verified_blocks)

        for curBlk in self.verified_blocks:
            points = len(curBlk.transactions)
            for tmpBlk in self.verified_blocks:
                if curBlk == tmpBlk:
                    continue
                for i in range(min_transactions):
                    if curBlk.transactions[i].size >= tmpBlk.transactions[i].size:
                        points += 1
    
            # Highest Points Check
            if points >= max_point:
                max_point = points
                highestBlock = curBlk
 
        # Return the highest block
        return highestBlock

    def verification_block(self, new_block, previous_block):
        if previous_block.index + 1 != new_block.index:
            return False
        if previous_block.hash != new_block.previous_hash:
            return False
        if self.blockchain.calculate_hash(new_block.index, 
            new_block.previous_hash, new_block.timestamp, 
            new_block.transactions, new_block.nonce) != new_block.hash:
            return False
        if new_block.block_generation_time > 300:
            return False
        return True
    
    def handle_penalty(self):
        # Handle the penalty by looping while checking for stop_event
        end_time = time.time() + self.penalty_time
        while time.time() < end_time:
            if self.stop_event.is_set():
                return
        self.penalty_event.clear()

def main():
    blockchain = Blockchain(4)
    max_blocks = 3
    network_queues = []
    network_stand_down_event = []
    network_penalty_event = []
    stop_event = threading.Event()

    nodes = [Node(i, blockchain, network_queues, network_stand_down_event, network_penalty_event, max_blocks, stop_event) for i in range(1,4)]

    for node in nodes:
        network_queues.append(node.local_queue)
        network_stand_down_event.append(node.stand_down_event)
        network_penalty_event.append(node.penalty_event)

    threads = []
    for node in nodes:
        t1 = threading.Thread(target=node.mine_block)
        t2 = threading.Thread(target=node.receive_block)
        t3 = threading.Thread(target=node.stand_down)
        t1.start()
        t2.start()
        t3.start()
        threads.append(t1)
        threads.append(t2)
        threads.append(t3)

    for t in threads:
        t.join()

    for block in blockchain.chain:
        print("\nIndex:", block.index)
        print("Miner: Node", block.miner_id)
        print("Previous Hash:", block.previous_hash)
        print("Timestamp:", block.timestamp)
        print("Block generation time:", block.block_generation_time)
        print("Hash:", block.hash)
        print("Nonce:", block.nonce)
        print("Transactions:", end=" ")
        for tx in block.transactions:
            print("{" + tx.transaction_id + ":" + str(tx.size) + "}", end="")
        print("")
        print("-" * 30)



if __name__ == "__main__":
    main()
