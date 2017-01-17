# -*- coding: utf-8 -*-
#
# This file is part of EUDAT B2Share.
# Copyright (C) 2016 CERN.
#
# B2Share is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# B2Share is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with B2Share; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""B2Share load test for a given site."""

from multiprocessing import Pool
import time
import json
import requests

from urllib.parse import urljoin


NUM_PROCESSES = 1
NUM_TOTAL_RECORDS = 10


def main(num_processes, num_total_records):
    time1 = time.time()
    # start 4 worker processes
    with Pool(processes=num_processes) as pool:
        for i in range(num_total_records):
            pool.apply_async(create_and_publish_record, (i,))

        pool.close()
        pool.join()

    time2 = time.time()
    print ('\n\nCreating and publishing {} records took {} seconds'
           .format(num_total_records, (time2-time1)))


def create_and_publish_record(index, url, access_token):
    url = url or 'https://b2share.local/api/records'
    access = {'access_token': access_token}
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json'}

    # create record
    metadata = {
        "titles": [{"title":"TestRest"}],
        "community": "e9b9792e-79fb-4b07-b6b4-b9c2bd06d095",
        "open_access": True,
        "community_specific": {},
    }
    r = requests.post(url, data=json.dumps(metadata),
                      params=access, headers=headers, verify=False)
    expect(r)

    rec_id = json.loads(r.text).get('id')
    rec_url = urljoin(url+'/', rec_id)
    draft_url = rec_url+'/draft'

    # publish record
    patch = [{"op": "add", "path":"/publication_state", "value": "submitted"}]
    r = requests.patch(draft_url, data=json.dumps(patch),
                       params=access, headers=headers, verify=False)
    expect(r)

def expect(req):
    if req.status_code >= 300:
        print("Request returned {}".format(req.status_code))

if __name__ == '__main__':
    main(NUM_PROCESSES, NUM_TOTAL_RECORDS)
