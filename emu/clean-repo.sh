#! /bin/bash
commit=commit

mkdir -p $2
git -C $2 init
for line in $(tac $commit); do
        git -C $1 checkout $line
        rsync -avc --exclude='.git/' $1/ $2/ --delete
        git -C $2 add -A
        git -C $2 commit -m "$(git -C $1 log -n 1 --pretty=format:%s $line)"
done
