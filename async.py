import logging
import threading
import time
import queue

def thread_function():
	name = 1
	logging.info("Thread %s: starting", name)
	time.sleep(2)
	logging.info("Thread %s: finishing", name)
	return "penis"

if __name__ == "__main__":
	format = "%(asctime)s: %(message)s"
	logging.basicConfig(format=format, level=logging.INFO,
						datefmt="%H:%M:%S")

	que = queue.Queue()
	# x = threading.Thread(target=lambda q: q.put(thread_function()), args=(que,))
	logging.info("Main    : before creating thread")
	# x = threading.Thread(target=thread_function, args=(1,), daemon = True)
	# x = threading.Thread(target=thread_function, args=(1,))
	logging.info("Main    : before running thread")
	# x.start()
	logging.info("Main    : wait for the thread to finish")
	# x.join() #daemon are background threads that the main func does not wait for to complete, so you must use x.join to tell the fun to wait
	logging.info("Main    : all done")
	print(que)
	if que.empty(): #this empty method is dog shit, doesn't work
		print("we good")
		try:
			result = que.get(False)
		except Exception as e:
			print("caught error")
