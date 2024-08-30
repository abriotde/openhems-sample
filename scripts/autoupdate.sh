#!/bin/bash

source config.sh

echo "OpenHEMS autoupdate : Check for new version"
cd $TMP_DIR
rm -rf $TMP_DIR/openhems-sample
mkdir $TMP_DIR/openhems-sample
cd $TMP_DIR/openhems-sample
wget -q https://raw.githubusercontent.com/abriotde/openhems-sample/main/version
diff -b $TMP_DIR/openhems-sample/version "$OPENHEMS_PATH/version"
ok=$?
if [ $ok == 1 ]; then
	echo "OpenHEMS autoupdate : New version available, get it"
	git clone https://github.com/abriotde/openhems-sample.git
	chown -R olimex:olimex openhems-sample
	if [ $? != 0 ]; then
		echo "OpenHEMS autoupdate : Fail get new version"
		exit 1
	fi
	# Warning : do not erase configs...
	rsync -apzh --delete --exclude='.git' --exclude='config' openhems-sample $OPENHEMS_PATH/..
	echo "OpenHEMS autoupdate : Stop service"
	systemctl stop openhems.service
	sleep 3
	echo "OpenHEMS autoupdate : Start service"
	systemctl start openhems.service
	echo "OpenHEMS autoupdate : succeeded"
elif [ $ok == 0 ]; then
	echo "OpenHEMS autoupdate : No new version available. Nothing more to do."
else
	echo "OpenHEMS autoupdate : Error updating : $ok for 'diff -b $TMP_DIR/openhems-sample/version $OPENHEMS_PATH/version'."
fi
