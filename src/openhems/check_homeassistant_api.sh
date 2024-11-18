#!/bin/bash

curl -v -H "Accept: application/json" -H "Content-type: application/json" \
 -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmOTM4ZTFmY2FjNTA0MWEyYWZkYjEyOGYyYTJlNGNmYiIsImlhdCI6MTcyNjU2NTU1NiwiZXhwIjoyMDQxOTI1NTU2fQ.3DdEXGsM3cg5NgMUKj2k5FsEG07p2AkRF_Ad-CljSTQ" \
 -d '{"entity_id": "switch.tz3000_2putqrmw_ts011f_commutateur_2"}' \
 http://192.168.1.202:8123/api/services/switch/turn_on

exit

curl -v -H "Accept: application/json" -H "Content-type: application/json" \
 -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmOTM4ZTFmY2FjNTA0MWEyYWZkYjEyOGYyYTJlNGNmYiIsImlhdCI6MTcyNjU2NTU1NiwiZXhwIjoyMDQxOTI1NTU2fQ.3DdEXGsM3cg5NgMUKj2k5FsEG07p2AkRF_Ad-CljSTQ" \
 -X GET http://192.168.1.202:8123/api/states/switch.tz3000_2putqrmw_ts011f_commutateur_2
 
 exit

