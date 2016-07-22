#!/bin/bash

# Load RVM into a shell session *as a function*
export PATH="$HOME/.rbenv/bin:$PATH" 
eval "$(rbenv init -)"
DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
# echo $DIR
cd $2
ruby $DIR/string_formatter_tester.rb $1/db.sqlite3 $DIR/shape.format > $3/shape.out
ruby $DIR/string_formatter_tester.rb $1/db.sqlite3 $DIR/bird.format > $3/bird.out

awk  'BEGIN{FS="\t"; print("\"Day Due\",\"Box\",\"Task\"")}; /.*\t.*/ {print("\""$1 "\",\"" $2 "\",\"" $3 "\"");}' $3/bird.out > $3/BirdNesting-OutstandingTasks-`date +"%Y-%m-%d"`.csv