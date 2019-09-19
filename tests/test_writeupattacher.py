'''
Testing writeup attacher
'''
import time
import mock
from mock import patch
import synapseclient
import synapseutils
from synapseclient.annotations import to_submission_status_annotations

import challengeutils.utils
import challengeutils.writeup_attacher
from challengeutils.writeup_attacher import _create_archive_writeup
from challengeutils.writeup_attacher import archive_writeup
from challengeutils.writeup_attacher import archive_writeups


SYN = mock.create_autospec(synapseclient.Synapse)
ENTITY = synapseclient.File(name='test', parentId="syn123", id="syn222")
SUBMISSION = synapseclient.Submission(name="wow", entityId=ENTITY['id'],
                                      evaluationId="123", versionNumber=2,
                                      entity=ENTITY, id=333)


def test__create_archive_writeup():
    """Create archive writeup project"""
    archived_name = (f"Archived {SUBMISSION.entity.name} 10000 "
                     f"{SUBMISSION.id} {SUBMISSION.entityId}")
    # This 'project' is used for the assert call
    project = synapseclient.Project(archived_name)
    # The returned project must have id as the id is used in copy call
    return_project = synapseclient.Project(archived_name, id="syn888")
    with patch.object(SYN, "store",
                      return_value=return_project) as patch_syn_store,\
         patch.object(time, "time", return_value=10),\
         patch.object(synapseutils, "copy") as patch_syn_copy:
        archive_proj = _create_archive_writeup(SYN, SUBMISSION)
        assert archive_proj == return_project
        patch_syn_store.assert_called_once_with(project)
        patch_syn_copy.assert_called_once_with(SYN, SUBMISSION.entityId,
                                               archive_proj.id)

def test_alreadyarchived_archive_writeup():
    """
    If the archive annotation already exists the writeup shouldn't be archived,
    making sure that the archived entity id is returned.
    """
    annotations = {"archived": "1"}
    syn_annots = to_submission_status_annotations(annotations)
    submission_status = synapseclient.SubmissionStatus(annotations=syn_annots)
    with patch.object(SYN, "getSubmission",
                      return_value=SUBMISSION) as patch_getsub,\
         patch.object(SYN, "getSubmissionStatus",
                      return_value=submission_status) as patch_getsubstatus,\
         patch.object(challengeutils.writeup_attacher,
                      "_create_archive_writeup") as patch__archive,\
         patch.object(challengeutils.utils,
                      "update_single_submission_status") as patch_update,\
         patch.object(SYN, "store") as patch_syn_store:
        archive_proj = archive_writeup(SYN, SUBMISSION.id)
        patch_getsub.assert_called_once_with(SUBMISSION.id, downloadFile=False)
        patch_getsubstatus.assert_called_once_with(SUBMISSION.id)
        patch__archive.assert_not_called()
        patch_update.assert_not_called()
        patch_syn_store.assert_not_called()
        # The archive project entity id should be returned
        assert archive_proj == annotations['archived']


def test_notarchive_archive_writeup():
    """Archive writeup if there is not an archive"""
    return_project = synapseclient.Project("test", id="syn2222")
    annotations = {"archived": "syn2222"}
    syn_annots = to_submission_status_annotations(annotations)
    archive_substatus = synapseclient.SubmissionStatus(annotations=syn_annots)
    with patch.object(SYN, "getSubmission",
                      return_value=SUBMISSION) as patch_getsub,\
         patch.object(SYN, "getSubmissionStatus",
                      return_value=archive_substatus) as patch_getsubstatus,\
         patch.object(challengeutils.writeup_attacher,
                      "_create_archive_writeup",
                      return_value=return_project) as patch__archive,\
         patch.object(challengeutils.utils,
                      "update_single_submission_status",
                      return_value=archive_substatus) as patch_update,\
         patch.object(SYN, "store") as patch_syn_store:
        archive_proj = archive_writeup(SYN, SUBMISSION.id, rearchive=True)
        patch_getsub.assert_called_once_with(SUBMISSION.id, downloadFile=False)
        patch_getsubstatus.assert_called_once_with(SUBMISSION.id)
        patch__archive.assert_called_once_with(SYN, SUBMISSION)
        patch_update.assert_called_once_with(archive_substatus,
                                             annotations)
        patch_syn_store.assert_called_once_with(archive_substatus)
        assert archive_proj == return_project.id


def test_forcerearchive_archive_writeup():
    """
    Archive writeup even if there is already an archive but rearchive=True
    """
    submission_status = synapseclient.SubmissionStatus(annotations={})
    return_project = synapseclient.Project("test", id="syn2222")
    annotations = {"archived": "syn2222"}
    syn_annots = to_submission_status_annotations(annotations)
    archive_substatus = synapseclient.SubmissionStatus(annotations=syn_annots)
    with patch.object(SYN, "getSubmission",
                      return_value=SUBMISSION) as patch_getsub,\
         patch.object(SYN, "getSubmissionStatus",
                      return_value=submission_status) as patch_getsubstatus,\
         patch.object(challengeutils.writeup_attacher,
                      "_create_archive_writeup",
                      return_value=return_project) as patch__archive,\
         patch.object(challengeutils.utils,
                      "update_single_submission_status",
                      return_value=archive_substatus) as patch_update,\
         patch.object(SYN, "store") as patch_syn_store:
        archive_proj = archive_writeup(SYN, SUBMISSION.id)
        patch_getsub.assert_called_once_with(SUBMISSION.id, downloadFile=False)
        patch_getsubstatus.assert_called_once_with(SUBMISSION.id)
        patch__archive.assert_called_once_with(SYN, SUBMISSION)
        patch_update.assert_called_once_with(submission_status,
                                             annotations)
        patch_syn_store.assert_called_once_with(archive_substatus)
        assert archive_proj == return_project.id


def test_default_params_archive_writeups():
    """Archive writeups given evaluation queue"""
    eval_obj = synapseclient.Evaluation(id="foo", contentSource="syn123",
                                        name="test")
    with patch.object(SYN, "getEvaluation",
                      return_value=eval_obj) as patch_geteval,\
         patch.object(SYN, "getSubmissionBundles",
                      return_value=[(SUBMISSION, "test")]) as patch_getsub,\
         patch.object(challengeutils.writeup_attacher,
                      "archive_writeup",
                      return_value="syn1234") as patch_archive_writep:
        archived = archive_writeups(SYN, 1234)
        patch_geteval.assert_called_once_with(1234)
        patch_getsub.assert_called_once_with(eval_obj, status="VALIDATED")
        patch_archive_writep.assert_called_once_with(SYN, SUBMISSION.id,
                                                     rearchive=False)
        assert archived == ['syn1234']


def test_nondefault_params_archive_writeups():
    """Archive writeups given evaluation queue with non default params"""
    eval_obj = synapseclient.Evaluation(id="foo", contentSource="syn123",
                                        name="test")
    with patch.object(SYN, "getEvaluation") as patch_geteval,\
         patch.object(SYN, "getSubmissionBundles",
                      return_value=[(SUBMISSION, "test")]) as patch_getsub,\
         patch.object(challengeutils.writeup_attacher,
                      "archive_writeup",
                      return_value="syn1234") as patch_archive_writep:
        archived = archive_writeups(SYN, eval_obj, status="SCORED",
                                    rearchive=True)
        patch_geteval.assert_not_called()
        patch_getsub.assert_called_once_with(eval_obj, status="SCORED")
        patch_archive_writep.assert_called_once_with(SYN, SUBMISSION.id,
                                                     rearchive=True)
        assert archived == ['syn1234']


def test_multiple_submissions_archive_writeups():
    """
    Archive writeups given evaluation queue that has multiple submissions
    """
    eval_obj = synapseclient.Evaluation(id="foo", contentSource="syn123",
                                        name="test")
    returned_bundle = [(SUBMISSION, "test"), (SUBMISSION, "test")]
    with patch.object(SYN, "getEvaluation") as patch_geteval,\
         patch.object(SYN, "getSubmissionBundles",
                      return_value=returned_bundle) as patch_getsub,\
         patch.object(challengeutils.writeup_attacher,
                      "archive_writeup",
                      return_value="syn1234") as patch_archive_writep:
        archived = archive_writeups(SYN, eval_obj)
        patch_geteval.assert_not_called()
        patch_getsub.assert_called_once_with(eval_obj, status="VALIDATED")
        assert patch_archive_writep.call_count == 2
        assert archived == ['syn1234', 'syn1234']
