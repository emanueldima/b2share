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
# WITHOUT ANY WARRANTY; without even the implied warr   anty of
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

"""B2Share Record API."""

from elasticsearch.exceptions import NotFoundError
from invenio_db import db
from invenio_pidstore.resolver import Resolver
from invenio_pidstore.models import PersistentIdentifier, PIDStatus
from invenio_deposit.api import Deposit
from b2share.modules.deposit.api import Deposit as B2ShareDeposit
from invenio_records.models import RecordMetadata
from invenio_records_files.models import RecordsBuckets
from invenio_records.api import Record
from invenio_records_files.api import Record
from invenio_files_rest.models import Bucket
# from b2share.modules.deposit.fetchers import b2share_deposit_uuid_fetcher
from b2share.modules.deposit.providers import DepositUUIDProvider
from b2share.modules.records.fetchers import b2share_record_uuid_fetcher
from invenio_indexer.api import RecordIndexer
from invenio_pidrelations.contrib.versioning import PIDVersioning

class B2ShareRecord(Record):
    """B2Share record class."""

    @property
    def pid(self):
        """Return an instance of record PID."""
        pid = b2share_record_uuid_fetcher(self.id, self)
        return PersistentIdentifier.get(pid.pid_type,
                                        pid.pid_value)
    def delete(self):
        """Delete a record."""
        pid = self.pid
        # Fetch deposit id from record and resolve deposit record and pid.
        depid = PersistentIdentifier.get(DepositUUIDProvider.pid_type,
                                         pid.pid_value)
        if depid.status == PIDStatus.REGISTERED:
            depid, deposit = Resolver(
                pid_type=depid.pid_type,
                object_type='rec',
                # Retrieve the deposit with the Record class on purpose as the current
                # Deposit api prevents the deletion of published deposits.
                getter=B2ShareDeposit.get_record,
            ).resolve(depid.pid_value)
            deposit.delete()

        # Mark all record's PIDs as DELETED
        all_pids = PersistentIdentifier.query.filter(
            PersistentIdentifier.object_type == pid.object_type,
            PersistentIdentifier.object_uuid == pid.object_uuid,
        ).all()
        for rec_pid in all_pids:
            if not rec_pid.is_deleted():
                rec_pid.delete()

        # Mark the bucket as deleted
        # delete all buckets linked to the deposit
        res = Bucket.query.join(RecordsBuckets).\
            filter(RecordsBuckets.bucket_id == Bucket.id,
                   RecordsBuckets.record_id == self.id).all()
        for bucket in res:
            bucket.deleted = True

        # Mark the record and deposit as deleted. The record is unindexed
        # via the trigger on record deletion.
        super(B2ShareRecord, self).delete()

        version_master = PIDVersioning(child=pid)
        # If the parent has no other children and no draft child
        # mark it as deleted
        if not version_master.children.all():
            if not version_master.draft_child:
                version_master.parent.delete()
        else:
            # Reindex the "new" last published version in order to have
            # its "is_last_version" up to date.
            RecordIndexer().index_by_id(version_master.last_child.object_uuid)
