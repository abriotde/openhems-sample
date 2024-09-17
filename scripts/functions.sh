#!/bin/bash

# https://linuxfr.org/news/s-m-a-r-t-badblocks-badblocks2

function wait_homeassistant_container_up {
	docker container ls -a
	docker container ps
	echo "Waiting Home-Assistant server is ready"
	while [ `wget -O - http://127.0.0.1:8123 2>/dev/null|wc -c` -lt 1000 ]; do
		echo -n .
		sleep 1
	done
	echo "Ok, waiting 30 seconds"
	sleep 30
}

