# -*- coding: utf-8 -*-
# LOGEDOSOFT

from __future__ import unicode_literals
import frappe, json, uuid, mimetypes, os
from frappe import msgprint, _
#from six import string_types, itervalues, iteritems

from frappe.model.document import Document
from drive.api.files import create_folder
#from frappe.utils import cstr, flt, cint, nowdate, add_days, comma_and, now_datetime, ceil, today, formatdate, encode, format_time
#from frappe.utils.csvutils import build_csv_response

#from erpnext.manufacturing.doctype.bom.bom import validate_bom_no, get_children
#from erpnext.manufacturing.doctype.work_order.work_order import get_item_details, make_job_card, make_stock_entry, stop_unstop
#from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
#from erpnext.stock.doctype.batch.batch import get_batch_qty

def get_folder_entity(strParentEntityID, strFolderName):
	#Check if given FolderName is exist under the Parent Entity ID
	#If it exists returns Entity Document
	docResult = None

	dctDriveEntity = frappe.db.get_list('Drive Entity',
		filters={
			'parent_drive_entity': strParentEntityID,
			'title': strFolderName,
			'is_active': 1,
			'is_group': 1
		},
		fields=['name'],
		page_length=1,
		as_list=False
	)

	if dctDriveEntity:
		docResult = frappe.get_doc("Drive Entity", dctDriveEntity[0]['name'])

	return docResult

def process_attached_file(docFile, method = None):
	#Purpose: Attached file should be accessible from Drive.
	#Algorithm: Check if attached doctype is set in the JD Settings.
	#If it is set, check folder locations and create any parent folder if it is neccesary.
	#Create a Drive Entity for the file and set its parent according to JD settings.
	#https://frappeframework.com/docs/v14/user/en/basics/doctypes/controllers#controller-hooks

	if method == "after_insert":
		docJDSettings = frappe.get_doc("JD Settings")
		for rowFolderSettings in docJDSettings.folder_details:
			if docFile.attached_to_doctype == rowFolderSettings.data_type:
				#File's doctype has a setting in the JD Settings.
				strParentID = docJDSettings.drive_main_entity #Will store the parent ID
				
				docAttached = frappe.get_doc(docFile.attached_to_doctype, docFile.attached_to_name)
				print(f"rowFolderSettings.parent_folder={rowFolderSettings.parent_folder} rowFolderSettings.parent_entity={rowFolderSettings.parent_entity}")
				#Check Parent folder
				if rowFolderSettings.parent_folder != "":
					strParsedParentFolderName = frappe.render_template(rowFolderSettings.parent_folder, context={"doc": docAttached}, is_path=False)
					docParentEntity = get_folder_entity(strParentID, strParsedParentFolderName)
					if docParentEntity is None:
						docParentEntity = create_folder(strParsedParentFolderName, strParentID)
						print(f"docParentEntity={docParentEntity} CREATED")
					else:
						print(f"docParentEntity={docParentEntity} IS FOUND")
					
					strParentID = docParentEntity.name
				
				#Check folder
				if rowFolderSettings.folder != "":
					strParsedFolderName = frappe.render_template(rowFolderSettings.folder, context={"doc": docAttached}, is_path=False)
					docFolderEntity = get_folder_entity(strParentID, strParsedFolderName)
					if docFolderEntity is None:
						docFolderEntity = create_folder(strParsedFolderName, strParentID)
						print(f"docFolderEntity={docFolderEntity} CREATED")
					else:
						print(f"docFolderEntity={docFolderEntity} IS FOUND")

					strParentID = docFolderEntity.name

				#Check Sub folder
				if rowFolderSettings.sub_folder != "":
					strParsedSubFolderName = frappe.render_template(rowFolderSettings.sub_folder, context={"doc": docAttached}, is_path=False)
					docSubFolderEntity = get_folder_entity(strParentID, strParsedSubFolderName)
					if docSubFolderEntity is None:
						docSubFolderEntity = create_folder(strParsedSubFolderName, strParentID)
						print(f"docSubFolderEntity={docSubFolderEntity} CREATED")
					else:
						print(f"docSubFolderEntity={docSubFolderEntity} IS FOUND")

					strParentID = docSubFolderEntity.name

				#We've created the folders. Let's add the file in that parent
				docNewDriveEntity = frappe.new_doc("Drive Entity")
				docNewDriveEntity.name = uuid.uuid4().hex
				docNewDriveEntity.title = docFile.file_name
				docNewDriveEntity.old_parent = strParentID
				docNewDriveEntity.parent_drive_entity = strParentID
				docNewDriveEntity.path = f"{frappe.local.site}/{docFile.file_url}"
				docNewDriveEntity.file_size = docFile.file_size
				docNewDriveEntity.version = 1
				docNewDriveEntity.is_active = True
				mime_type, encoding = mimetypes.guess_type(docNewDriveEntity.path)
				docNewDriveEntity.mime_type = mime_type
				file_name, file_ext = os.path.splitext(docFile.file_name)
				docNewDriveEntity.file_ext = file_ext
				docNewDriveEntity.insert()
				docNewDriveEntity.add_comment("Comment", _("Created for the {0} {1}").format(docFile.attached_to_doctype, docFile.attached_to_name))

		frappe.get_doc(dict(
			doctype='Error Log',
			method=f"File Drive Operation for {docFile.attached_to_name}",
			error = f"{docFile.attached_to_doctype} in {method}"
		)).insert()

@frappe.whitelist()
def create_project_folders(strProjectName, docProject):
	#We will create folders in the Drive app with permissions
	blnResult = True

	docProject = frappe.get_doc(json.loads(docProject))

	frappe.msgprint(f"{strProjectName} is processing")

	docJDSettings = frappe.get_single("JD Settings")
	for rowSetting in docJDSettings.folder_details:
		if rowSetting.data_type == "Project":
			strProjectParsedFolder = frappe.render_template(rowSetting.folder, context={"doc": docProject}, is_path=False)
			frappe.msgprint(f"Folder Name={strProjectParsedFolder}")
			#docProjectEntity = copy_folder_with_permission(docJDSettings.template_folder, strProjectFolder, docJDSettings.project_folder)
			docDEProject = create_folder(strProjectParsedFolder, docJDSettings.project_folder)
			print("========================================================================")
			docDEProjectParent = frappe.get_doc("Drive Entity", docDEProject.parent_drive_entity)
			print(f"docDEProject={docDEProject} folder created in the {docDEProjectParent.title}")
			docDEProject = copy_folder_with_permission(docDEProject, frappe.get_doc("Drive Entity", docJDSettings.template_folder))
			print(f"docDEProject={docDEProject} processed")

	frappe.msgprint(f"{strProjectName} processed")

	return blnResult

def create_folder(strNewFolderName, strParentEntityID):
	print(f"create_folder with ({strNewFolderName}, {strParentEntityID})")
	docNewDriveEntity = frappe.new_doc("Drive Entity")
	docNewDriveEntity.name = uuid.uuid4().hex
	docNewDriveEntity.title = strNewFolderName
	docNewDriveEntity.is_group = 1
	docNewDriveEntity.old_parent = strParentEntityID
	docNewDriveEntity.parent_drive_entity = strParentEntityID
	#docNewDriveEntity.version = 1
	docNewDriveEntity.is_active = True
	docNewDriveEntity.color = "#98A1A9"
	docNewDriveEntity.insert()
	print(f"docNewDriveEntity={docNewDriveEntity} {docNewDriveEntity.title} created")
	#copy_folder_permission(strParentEntityID, docNewDriveEntity)

	return docNewDriveEntity

def copy_folder_permission(strParentEntityID, docNewDriveEntity):
	#First we need to get if any permission exist for the strParentEntityID. Use get_list for docshare.
	#Then we need to set them for the docNewDriveEntity. To accomplish this we will create docShare document

	print(f"copy_folder_permission with ({strParentEntityID}, {docNewDriveEntity})")
	dctSourceDocShare = frappe.db.get_list('DocShare',
		filters={
			'share_doctype': "Drive Entity",
			'share_name': strParentEntityID
		},
		fields=['name', 'user', 'read', 'write', 'share', 'notify_by_email'],
		page_length=9999,
		as_list=False
	)
	print(f"dctSourceDocShare IS {dctSourceDocShare}")
	for source_share in dctSourceDocShare:
		docNewDriveEntity.share(source_share.user, source_share.write, source_share.share, source_share.notify_by_email)
		print(f"docNewDriveEntity={docNewDriveEntity.title} SHARED WITH {source_share.user}")
		"""docNewDocShare = frappe.new_doc("Drive Entity")
		docNewDocShare.user = source_share.user
		docNewDocShare.share_doctype = "Drive Entity"
		docNewDocShare.share_name = docNewDriveEntity.name
		docNewDocShare.read = source_share.read
		docNewDocShare.write = source_share.write
		docNewDocShare.share = source_share.share
		docNewDocShare.notify_by_email = source_share.notify_by_email
		docNewDocShare.insert()"""

def copy_folder_with_permission(docDEParent, docDESource):
	#docDEParent = "Prj-101" => "M" (Folders which we are creating)
	#docDESource = "2023" (Folders in the template folder)

	docNewDriveEntity = None
	dctSubEntity = frappe.db.get_list('Drive Entity',
		filters={
			'parent_drive_entity': docDESource.name,
			'is_active': 1
		},
		fields=['name', 'title', 'is_group'],
		page_length=9999,
		as_list=False
	)
	print(f"dctSubEntity={dctSubEntity}")

	for sub_entity in dctSubEntity:
		print(f"sub_entity={sub_entity}")
		docDECurrent = create_folder(sub_entity.title, docDEParent.name)
		copy_folder_permission(sub_entity.name, docDECurrent)
		
		docNewDriveEntity = copy_folder_with_permission(docDECurrent, frappe.get_doc("Drive Entity", sub_entity.name))
		if docNewDriveEntity is None:
			print(f"docNewDriveEntity=NONE processed")
		else:
			print(f"docNewDriveEntity={docNewDriveEntity} {docNewDriveEntity.title} processed")

	return docNewDriveEntity