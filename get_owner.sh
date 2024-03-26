#!/bin/bash

FILE='./state.json'

if [ -z $1 ]; then
	echo "Please provide a hostname as argument!" >&2
	exit 1
fi

nodeinfo=$(cat $FILE | jq '.nodes | map(select(.nodeinfo.hostname == "'"$1"'"))')

if [ "$nodeinfo" == '[]' ]; then
	echo "No node with hostname $1 found!" >&2
	exit 2
fi


result=$(echo "$nodeinfo" | grep contact | awk -F ':' '{ print $2 }' | sed -e 's/\s*"\([^"]*\)"\s*,*/\1/')

if [ -z "$result" ]; then
	echo "$1 does not provide contact information!" >&2
	exit 3
fi

echo "$result"
