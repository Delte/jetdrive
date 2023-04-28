/*LOGEDOSOFT 2023*/

frappe.ui.form.on('Project', {
	refresh(frm) {
		frm.add_custom_button(__("Project Folders"), function() {
			frappe.msgprint("Custom Information");
			frappe.call({
				method: "jetdrive.jd_utils.create_project_folders",
				args: {
					strProjectName: frm.doc.name,
					docProject: frm.doc
				},
				callback: function (objResponse) {
					frappe.msgprint(objResponse);
				}
			});
		}, __("Create"));
	}
})