# -*- coding: utf-8 -*-
#
# This file is part of EUDAT B2Share.
# Copyright (C) 2018 University of Tuebingen.
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
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""B2Share directive API."""

from __future__ import absolute_import, print_function


from threading import Thread
import requests
import json
from datetime import datetime
from pprint import pprint
from flask import current_app
from flask_login import current_user
from invenio_db import db
from invenio_accounts.models import Role, User, userrole
from b2share.modules.communities import Community


def dex_dispatch(action_type, request, args, preceding):
    event = {
        'id': 12343,
        'time': datetime.now().isoformat(),
        'action': action_type, # one of: "DataAnalysis"...
        'preceding': preceding,
    }

    user = {
        'id': current_user.id,
        'name': "",
        'email': current_user.email,
        'role': find_current_user_roles(current_user.id),
    }

    resource = {
        'uri': request.url,
        'method': request.environ['REQUEST_METHOD'],
        'args': args,
    }

    environment = {
    }

    statistics = {
    }

    event_payload = {
        'event': event,
        'user': user,
        'resource': resource,
        'environment': environment,
        'statistics': statistics,
    }

    print('----  dex.dispatch: ')
    pprint(event_payload)

    dex_url = current_app.config.get('DIRECTIVE_ENGINE_URL')
    headers = {'Content-Type': 'application/json'}
    req = requests.post(dex_url, headers=headers,
                        data=json.dumps(event_payload))
    if req.status_code != 200:
        current_app.logger.error(
            "Error invoking directive engine, ret={}{}",
            req.status_code, req.data)
        return None
    else:
        ret_data = req.json()
        print('-> ')
        pprint(ret_data)
        return ret_data


def find_current_user_roles(user_id):
    roles_query = db.session.query(Role).join(userrole)
    roles = roles_query.filter_by(user_id=user_id).order_by(Role.name).all()
    def comm(rolename):
        return Community.get(id=rolename.split(':')[1])
    return [{
            'name': r.name,
            'description': r.description,
            'communityid': str(comm(r.name).id),
            'communityname': comm(r.name).name,
        } for r in roles]




