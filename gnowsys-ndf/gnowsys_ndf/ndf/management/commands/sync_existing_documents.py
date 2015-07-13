''' imports from installed packages '''
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

try:
  from bson import ObjectId
except ImportError:  # old pymongo
  from pymongo.objectid import ObjectId

''' imports from application folders/files '''
from gnowsys_ndf.ndf.models import node_collection, triple_collection
from gnowsys_ndf.ndf.models import Node
from gnowsys_ndf.settings import GSTUDIO_AUTHOR_AGENCY_TYPES


class Command(BaseCommand):

  help = " This script will add new field(s) into already existing documents " \
      + "(only if they doesn't exists) in your database."

  def handle(self, *args, **options):
    # Keep latest changes in field(s) to be added at top

    # adding all activated and logged-in user's id into author_set of "home" group ---
    all_authors = node_collection.find({"_type": "Author"})
    authors_list = [auth.created_by for auth in all_authors]

    home_group = node_collection.one({"_type":"Group", "name": "home"}) 
    prev_home_author_set = home_group.author_set
    total_author_set = list(set(authors_list + home_group.author_set))

    result = node_collection.collection.update({"_type": "Group", "name": u"home", "author_set": {"$ne": total_author_set} }, {"$set": {"author_set": total_author_set}}, upsert=False, multi=False )

    if result['updatedExisting']: # and result['nModified']:
        home_group.reload()
        print "\n Updated author_set of 'home' group:" + \
            "\n\t - Previously it was   : " + str(prev_home_author_set) + \
            "\n\t - Now it's updated to : " + str(home_group.author_set)

    
    # --------------------------------------------------------------------------
    # 'group_admin' of group should not be empty. So updating one for [] with creator of group.
    all_groups = node_collection.find({'_type': 'Group'})
    for each_group in all_groups:
        if not each_group.group_admin:
            res = node_collection.collection.update({'_id': ObjectId(each_group._id)}, {'$set': {'group_admin': [each_group.created_by]}}, upsert=False, multi=False)

            if res['updatedExisting']:
                each_group.reload()
                print 'updated group_admin of: ' + each_group.name + ' from [] to :' + unicode(each_group.group_admin)


    # --------------------------------------------------------------------------
    # removing <'partner': bool> field from Group objects
    res = node_collection.collection.update({'_type': {'$in': ['Group']}}, {'$unset': {'partner': False }}, upsert=False, multi=True)

    if res['updatedExisting']: # and res['nModified']:
        print "\n Removed 'partner' field from " + res['n'].__str__() + " Group instances."


    # --------------------------------------------------------------------------
    # Adding <'moderation_level': -1> field to Group objects
    node_collection.collection.update({'_type': {'$in': ['Group']}, 'edit_policy': {'$nin': ['EDITABLE_MODERATED']}}, {'$set': {'moderation_level': -1 }}, upsert=False, multi=True)

    if res['updatedExisting']: # and res['nModified']:
        print "\n Added 'moderation_level' field to " + res['n'].__str__() + " Group instances."


    # -----------------------------------------------------------------------------
    # Replacing invalid value of agency_type field belonging to Author node by "Other"
    res = node_collection.collection.update(
        {"_type": "Author", "agency_type": {"$nin": GSTUDIO_AUTHOR_AGENCY_TYPES}},
        {"$set": {"agency_type": u"Other"}},
        upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n Replacing invalid value of agency_type field belonging to Author node by 'Other'" + \
            "... #" + res["n"].__str__() + " records updated."


    # -----------------------------------------------------------------------------
    # From existing RelationType instance(s), finding Binary relationships
    # and Setting their "member_of" field's value as "Binary" (MetaType)
    mt_binary = node_collection.one({
        '_type': "MetaType", 'name': "Binary"
    })
    if mt_binary:
        res = node_collection.collection.update({
            "_type": "RelationType", "object_type.0": {"$not": {"$type": 4}}
        }, {
            "$set": {"member_of": [mt_binary._id]}
        },
            upsert=False, multi=True
        )
        if res["updatedExisting"]: # and res["nModified"]:
            print "\n 'member_of' field updated in following RelationType " \
                + "instance(s) representing 'Binary Relationships':", res["n"]

    # Replacing object_type of "trainer_of_course" & "master_trainer_of_course"
    # relationship from "Announced Course" to "NUSSD Course"
    nussd_course = node_collection.one({
        '_type': "GSystemType", 'name': "NUSSD Course"
    })
    if nussd_course:
        nussd_course_id = nussd_course._id
        res = node_collection.collection.update({
            '_type': "RelationType", 'name': "trainer_of_course", "object_value": {"$nin": [nussd_course_id]}
        }, {
            '$set': {'object_type': [nussd_course_id]}
        },
            upsert=False, multi=False
        )
        if res['updatedExisting']: # and res['nModified']:
            print "\n Replaced object_type of 'trainer_of_course' relationship" \
                + " from 'Announced Course' to 'NUSSD Course'."

        res = node_collection.collection.update({
            '_type': "RelationType", 'name': "master_trainer_of_course", "object_value": {"$nin": [nussd_course_id]}
        }, {
            '$set': {'object_type': [nussd_course_id]}
        },
            upsert=False, multi=False
        )
        if res['updatedExisting']: # and res['nModified']:
            print "\n Replaced object_type of 'master_trainer_of_course' relationship" \
                + " from 'Announced Course' to 'NUSSD Course'."

    # Appending attribute_type_set and relation_type_set fields to existing MetaType nodes
    res = node_collection.collection.update(
        {'_type': "MetaType", "attribute_type_set": {"$exists": False}, "relation_type_set": {"$exists": False}},
        {'$set': {'attribute_type_set': [], 'relation_type_set': []}},
        upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n Appending attribute_type_set and relation_type_set fields to existing MetaType nodes."

    # Renames RelaionType names -- "has_corresponding_task" to "has_current_approval_task"
    res = node_collection.collection.update(
        {'_type': "RelationType", 'name': u"has_corresponding_task"}, 
        {'$set': {'name': u"has_current_approval_task"}}, 
        upsert=False, multi=False
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'name' field updated of RelationType (Renamed from has_corresponding_task to has_current_approval_task)"

    # Replaces "for_acourse" RelationType's object_cardinality field's value from 1 to 100
    res = node_collection.collection.update(
        {'_type': "RelationType", 'name': "for_acourse"}, 
        {'$set': {'object_cardinality': 100}}, 
        upsert=False, multi=False
    )

    if res['updatedExisting']: # and res['nModified']:
        print "\n Replaced 'for_acourse' RelationType's 'object_cardinality' field's value from 1 to 100."
    
    file_gst = node_collection.one({'_type':'GSystemType', 'name': 'File'}) 
    pandora_video_st = node_collection.one({'_type':'GSystemType', 'name':'Pandora_video'})
    # Update the url field of all nodes 
    # if pandora_video_st:
    #     nodes = node_collection.find({'member_of': {'$nin':[pandora_video_st._id],'$in':[file_gst._id]},'access_policy':'PUBLIC' })
    #     site = Site.objects.get(pk=1)
    #     site = site.domain.__str__()
    #     site = "127.0.0.1:8000" if (site == u'example.com') else site

    #     count = 0

    #     for each in nodes:
    #         grp_name = node_collection.one({'_id': ObjectId(each.group_set[0]) }).name
    #         if "/" in each.mime_type:
    #             filetype = each.mime_type.split("/")[1]
            
    #             url_link = "http://" + site + "/" + grp_name.replace(" ","%20").encode('utf8') + "/file/readDoc/" + str(each._id) + "/" + str(each.name) + "." + str(filetype)

    #             if each.url != unicode(url_link):
    #                 node_collection.collection.update({'_id':each._id},{'$set':{'url': unicode(url_link) }})
    #                 count = count + 1

    #     if count:
    #         print "\n 'url' field updated in following no. of documents: ", count

    # Update pandora videos 'member_of', 'created_by', 'modified_by', 'contributors' field 
    if User.objects.filter(username='nroer_team').exists():
        auth_id = User.objects.get(username='nroer_team').pk
        if auth_id and pandora_video_st:
            res = node_collection.collection.update(
                {'_type': 'File', 'member_of': {'$in': [pandora_video_st._id]}, 'created_by': {'$ne': auth_id} }, 
                {'$set': {'created_by': auth_id, 'modified_by': auth_id, 'member_of':[file_gst._id, pandora_video_st._id]}, '$push': {'contributors': auth_id} },
                upsert=False, multi=True
            )

            if res['updatedExisting']: # and res['nModified']:
                print "\n 'created_by, modified_by & contributors' field updated for pandora videos in following no. of documents: ", res['n']


    # Update prior_node for each node in DB who has its collection_set
    all_nodes = node_collection.find({'_type': {'$in': ['GSystem', 'File', 'Group']},'collection_set': {'$exists': True, '$not': {'$size': 0}} })
    count = 0
    for each in all_nodes:
        if each.collection_set:
            for l in each.collection_set:
                obj = node_collection.one({'_id': ObjectId(l) })
                if obj:
                    if each._id not in obj.prior_node:
                        node_collection.collection.update({'_id':obj._id},{'$push':{'prior_node': ObjectId(each._id) }})
                        count = count + 1
                        
    if count:
        print "\n prior_node field updated in following no. of documents: ", count

    # Updating names (Stripped) in all theme , theme_items and topic documents
    theme_GST = node_collection.one({'_type':'GSystemType','name': 'Theme'})
    theme_item_GST = node_collection.one({'_type':'GSystemType','name': 'theme_item'})
    topic_GST = node_collection.one({'_type':'GSystemType','name': 'Topic'})
    if theme_GST and theme_item_GST and topic_GST:
        nodes = node_collection.find({'member_of': {'$in': [theme_GST._id, theme_item_GST._id,topic_GST._id]} })
        count = 0
        for each in nodes:
            if each.name != each.name.strip():
                node_collection.collection.update({'_id':ObjectId(each._id)},{'$set': {'name': each.name.strip()} })
                count = count + 1

        if count:
            print "\n Name field updated (Stripped) in following no. of documents: ", count

    # Update's "status" field from DRAFT to PUBLISHED for all TYPE's node(s)
    res = node_collection.collection.update(
        {'_type': {'$in': ["MetaType", "GSystemType", "RelationType", "AttributeType"]}, 'status': u"DRAFT"}, 
        {'$set': {'status': u"PUBLISHED"}}, 
        upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'status' field updated for all TYPE's node(s) in following no. of documents: ", res['n']

    # Update object_value of GAttribute(s) of "Assignee" AttributeType
    # Find those whose data-type is not list/Array
    # Replace those as list of value(s)
    assignee_at = node_collection.one(
        {'_type': "AttributeType", 'name': "Assignee"}
    )

    if assignee_at:
        res = 0
        assignee_cur = triple_collection.find(
            {'_type': "GAttribute", 'attribute_type.$id': assignee_at._id}
        )

        for each in assignee_cur:
            # If string
            ul_sv = []
            if type(each.object_value) in [str, unicode]:
                if "," in each.object_value and "[" in each.object_value and "]" in each.object_value:
                    ul_sv = each.object_value.strip("[]").replace(", ", ",").replace(" ,", ",").split(",")
                elif "," in each.object_value:
                    ul_sv = each.object_value.replace(", ", ",").replace(" ,", ",").split(",")
                elif "[" in each.object_value or "]" in each.object_value:
                    ul_sv = each.object_value.strip("[]").split(",")

                ul_id = []
                for u in ul_sv:
                    if not u.isdigit():
                        user = User.objects.get(username=u)
                    else:
                        user = User.objects.get(id=int(u))
                    if user:
                        if user.id not in ul_id:
                            ul_id.append(user.id)

                upres = triple_collection.collection.update(
                            {'_id': each._id}, 
                            {'$set': {'object_value': ul_id}}, 
                            upsert=False, multi=False
                        )
                res += upres['n']

            # If list
            elif type(each.object_value) == list:
                ul_id = []
                for u in each.object_value:
                    if type(u) in [str, unicode] and not u.isdigit():
                        if u.strip("[]"):
                            user = User.objects.get(username=u)
                    elif type(u) in [str, unicode] and u.isdigit():
                        if u.strip("[]"):
                            user = User.objects.get(id=int(u))
                    else:
                        user = User.objects.get(id=int(u))

                    if user:
                        if user.id not in ul_id:
                            ul_id.append(user.id)

                upres = triple_collection.collection.update(
                            {'_id': each._id}, 
                            {'$set': {'object_value': ul_id}}, 
                            upsert=False, multi=False
                        )
                res += upres['n']

        if res:
            print "\n Updated following no. of Assignee GAttribute document(s): ", res

    # Updates already created has_profile_pic grelations' status - Except latest one (PUBLISHED) others' are set to DELETED
    has_profile_pic = node_collection.one({'_type': "RelationType", 'name': u"has_profile_pic"})
    op = triple_collection.collection.aggregate([
        {'$match': {
        '_type': "GRelation",
        'relation_type.$id': has_profile_pic._id
        }},
        {'$group': {
        '_id': {'auth_id': "$subject"},
        'pp_data': {'$addToSet': {'gr_id': "$_id", 'status': "$status"}}
        }}
    ])

    res = 0
    for each in op["result"]:
        auth_id = each["_id"]["auth_id"]
        pub_id = None
        pub_res = 0
        del_id = []
        del_res = 0

        for l in each["pp_data"]:
            if l["status"] == u"PUBLISHED":
                pub_id = l["gr_id"]

            else:
                del_id.append(l["gr_id"])

        if not pub_id:
            pub_id = each["pp_data"][len(each["pp_data"])-1]["gr_id"]
            pub_res = node_collection.collection.update({'_id': pub_id}, {'$set': {'status': u"PUBLISHED"}}, upsert=False, multi=False)
            pub_res = pub_res['n']            
            del_id.pop()

        del_res = node_collection.collection.update({'_id': {'$in': del_id}}, {'$set': {'status': u"DELETED"}}, upsert=False, multi=True)

        if pub_res or del_res['n']:
            res += 1

    if res:
        print "\n Updated following no. of has_profile_pic GRelation document(s): ", res

    # Updates the value of object_cardinality to 100. So that teaches will behave as 1:M (one-to-many) relation.
    teaches = node_collection.one({'_type': "RelationType", 'name': "teaches"})
    res = node_collection.collection.update({'_id': teaches._id, 'object_cardinality': {'$ne': 100}}, 
            {'$set': {'object_cardinality': 100}}, 
            upsert=False, multi=False
        )
    if res["updatedExisting"]:
        print "\n 'teaches' RelationType updated with object_cardinality: 100. Changed document: ", res['n']
    else:
        print "\n 'teaches' RelationType: no need to update."

    # Replacing object_type of "has_course" relationship from "NUSSD Course" to "Announced Course"
    ann_course = node_collection.one({'_type': "GSystemType", 'name': "Announced Course"})
    if ann_course:
        res = node_collection.collection.update({'_type': "RelationType", 'name': "has_course"}, 
                {'$set': {'object_type': [ann_course._id]}}, 
                upsert=False, multi=False
              )
        if res['updatedExisting']: # and res['nModified']:
            print "\n Replaced object_type of 'has_course' relationship from 'NUSSD Course' to 'Announced Course'."

    # Adds "relation_set" field (with default value as []) to all documents belonging to GSystems.
    res = node_collection.collection.update({'_type': {'$nin': ["MetaType", "GSystemType", "RelationType", "AttributeType", "GRelation", "GAttribute", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'relation_set': {'$exists': False}}, 
                            {'$set': {'relation_set': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'relation_set' field added to following no. of documents: ", res['n']

    # Adds "attribute_set" field (with default value as []) to all documents belonging to GSystems.
    res = node_collection.collection.update({'_type': {'$nin': ["MetaType", "GSystemType", "RelationType", "AttributeType", "GRelation", "GAttribute", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'attribute_set': {'$exists': False}}, 
                            {'$set': {'attribute_set': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'attribute_set' field added to following no. of documents: ", res['n']

    # Adds "license" field (with default value as "") to all documents belonging to GSystems.
    res = node_collection.collection.update({'_type': {'$nin': ["MetaType", "GSystemType", "RelationType", "AttributeType", "GRelation", "GAttribute", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'license': {'$exists': False}}, 
                            {'$set': {'license': None}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'license' field added to following no. of documents: ", res['n']

    # Adding "Agency_type" field adding to group documents with default values
    res = node_collection.collection.update({'_type': {'$in': ['Group']}, 'agency_type': {'$exists': False}}, 
                            {'$set': {'agency_type': "Project" }}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
       print "\n 'agency_type' field added to 'Group' documents totalling to : ", res['n']

    # Adding "Agency_type" field adding to author documents with default values
    res = node_collection.collection.update({'_type': {'$in': ['Author']}, 'agency_type': {'$exists': False}}, 
                            {'$set': {'agency_type': "Others" }}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
       print "\n 'agency_type' field added to 'Author' documents totalling to : ", res['n']


    # Modify language field with unicode value if any document has language with dict datatype
    res = node_collection.collection.update({'language': {}},
                            {'$set': {'language': u""}}, 
                            upsert=False, multi=True
    )

    # Removing existing "cr_or_xcr" field with no default value
    res = node_collection.collection.update({'_type': {'$in': ['Group']}, 'cr_or_xcr': {'$exists': True}}, 
                            {'$unset': {'cr_or_xcr': False }}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
       print "\n Already existing 'cr_or_xcr' field removed from documents totalling to : ", res['n']

    # Adding "curricular" field with no default value
    res = node_collection.collection.update({'_type': {'$in': ['Group']}, 'curricular': {'$exists': False}}, 
                            {'$set': {'curricular': False }}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'curricular' field added to all Group documents totalling to : ", res['n']

    # Removing existing "partners" field with no default value
    res = node_collection.collection.update({'_type': {'$in': ['Group']}, 'partners': {'$exists': True}}, 
                            {'$unset': {'partners': False }}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
       print "\n Already existing 'partners' field removed from documents totalling to : ", res['n']

    # # Adding "partner" field with no default value
    # res = node_collection.collection.update({'_type': {'$in': ['Group']}, 'partner': {'$exists': False}}, 
    #                         {'$set': {'partner': False }}, 
    #                         upsert=False, multi=True
    # )
    # if res['updatedExisting']: # and res['nModified']:
    #     print "\n 'partner' field added to all Group documents totalling to : ", res['n']

    # Adding "preferred_languages" field with no default value
    res = node_collection.collection.update({'_type': {'$in': ['Author']}, 'preferred_languages': {'$exists': False}}, 
                            {'$set': {'preferred_languages': {}}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'preferred_languages' field added to all author documents totalling to : ", res['n']


    # Adding "rating" field with no default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'rating': {'$exists': False}}, 
                            {'$set': {'rating': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'rating' field added to following no. of documents: ", res['n']
    
    # Adds 'subject_scope', 'attribute_type_scope', 'object_value_scope' field (with default value as "") to all documents which belongs to GAttribute
    res = node_collection.collection.update({'_type': {'$in': ["Group", "Author"]}, 'group_admin': {'$exists': False}}, 
                            {'$set': {'group_admin': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'group_admin' field added to following no. of documents: ", res['n']

    # Adds 'subject_scope', 'attribute_type_scope', 'object_value_scope' field (with default value as "") to all documents which belongs to GAttribute
    res = triple_collection.collection.update({'_type': "GAttribute", 'subject_scope': {'$exists': False}, 'attribute_type_scope': {'$exists': False}, 'object_value_scope': {'$exists': False}}, 
                            {'$set': {'subject_scope':"", 'attribute_type_scope':"", 'object_value_scope': ""}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'subject_scope', 'attribute_type_scope', 'object_value_scope' fields added to following no. of documents: ", res['n']

    # Adds 'subject_scope', 'relation_type_scope', 'right_subject_scope' field (with default value as "") to all documents which belongs to GRelation
    res = triple_collection.collection.update({'_type': "GRelation", 'subject_scope': {'$exists': False}, 'relation_type_scope': {'$exists': False}, 'right_subject_scope': {'$exists': False}}, 
                            {'$set': {'subject_scope':"", 'relation_type_scope':"", 'right_subject_scope': ""}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n 'subject_scope', 'relation_type_scope', 'right_subject_scope' fields added to following no. of documents: ", res['n']

    # Adds "annotations" field (with default value as []) to all documents belonging to GSystems
    res = node_collection.collection.update({'_type': {'$nin': ["MetaType", "GSystemType", "RelationType", "AttributeType", "GRelation", "GAttribute", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'annotations': {'$exists': False}}, 
                            {'$set': {'annotations': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n annotations field added to following no. of documents: ", res['n']

    # Adds "group_set" field (with default value as []) to all documents except those which belongs to either GAttribute or GRelation
    res = node_collection.collection.update({'_type': {'$nin': ["GAttribute", "GRelation", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'group_set': {'$exists': False}}, 
                            {'$set': {'group_set': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n group_set field added to following no. of documents: ", res['n']

    # Adds "property_order" field (with default value as []) to all documents except those which belongs to either GAttribute or GRelation
    res = node_collection.collection.update({'_type': {'$nin': ["GAttribute", "GRelation", "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'property_order': {'$exists': False}}, 
                            {'$set': {'property_order': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n property_order field added to following no. of documents: ", res['n']

    # Adding "modified_by" field with None as it's default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'modified_by': {'$exists': False}}, 
                            {'$set': {'modified_by': None}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n modified_by field added to following no. of documents: ", res['n']

    # Adding "complex_data_type" field with empty list as it's default value
    res = node_collection.collection.update({'_type': 'AttributeType', 'complex_data_type': {'$exists': False}}, 
                            {'$set': {'complex_data_type': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n complex_data_type field added to following no. of documents: ", res['n']

    # Adding "post_node" field with empty list as it's default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'post_node': {'$exists': False}}, 
                            {'$set': {'post_node': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n post_node field added to following no. of documents: ", res['n']

    # Adding "collection_set" field with empty list as it's default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'collection_set': {'$exists': False}}, 
                            {'$set': {'collection_set': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n collection_set field added to following no. of documents: ", res['n']

    # Adding "location" field with no default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'location': {'$exists': False}}, 
                            {'$set': {'location': []}}, 
                            upsert=False, multi=True
    )
    if res['updatedExisting']: # and res['nModified']:
        print "\n location field added to following no. of documents: ", res['n'],"\n"

    # Adding "language" field with no default value
    res = node_collection.collection.update({'_type': {'$nin': ['GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'language': {'$exists': False}}, 
                            {'$set': {'language': unicode('')}}, 
                            upsert=False, multi=True
    )
    
    # Adding "access_policy" field
    # For Group documents, access_policy value is set depending upon their 
    # group_type values, i.e. either PRIVATE/PUBLIC whichever is there
    node_collection.collection.update({'_type': 'Group', 'group_type': 'PRIVATE'}, {'$set': {'access_policy': u"PRIVATE"}}, upsert=False, multi=True)
    node_collection.collection.update({'_type': 'Group', 'group_type': 'PUBLIC'}, {'$set': {'access_policy': u"PUBLIC"}}, upsert=False, multi=True)
    
    # For Non-Group documents which doesn't consits of access_policy field, add it with PUBLIC as it's default value
    node_collection.collection.update({'_type': {'$nin': ['Group', 'GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'access_policy': {'$exists': False}}, {'$set': {'access_policy': u"PUBLIC"}}, upsert=False, multi=True)
    
    node_collection.collection.update({'_type': {'$nin': ['Group', 'GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'access_policy': {'$in': [None, "PUBLIC"]}}, {'$set': {'access_policy': u"PUBLIC"}}, upsert=False, multi=True)
    node_collection.collection.update({'_type': {'$nin': ['Group', 'GAttribute', 'GRelation', "ReducedDocs", "ToReduceDocs", "IndexedWordList", "node_holder"]}, 'access_policy': "PRIVATE"}, {'$set': {'access_policy': u"PRIVATE"}}, upsert=False, multi=True)
    
    gstpage_node = node_collection.find_one({"name":"Page"})
    gstwiki = node_collection.find_one({"name":"Wiki page"})

    page_nodes = node_collection.find({"member_of":gstpage_node._id})
    for i in page_nodes:
        if gstwiki._id not in i.type_of:
            i.type_of.append(gstwiki._id)
            i.save()
        else:
            print i.name,"Page already Updated"	

    nodes = node_collection.find({"_type":"Author",
			'$or':[{'language_proficiency':{'$exists':False}},{'subject_proficiency':{'$exists':False}}]}) 
    for i in nodes:
		    node_collection.collection.update({'_id':ObjectId(i._id)}, {'$set':{'language_proficiency': '','subject_proficiency':'' }},upsert=False, multi=False)
		    print i.name, "Updated !!"	



