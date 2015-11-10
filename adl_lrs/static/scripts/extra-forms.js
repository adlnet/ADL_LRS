$(document).ready(function() {
	// Toggles the id_secret field when checkbox is checked
	$(function (){
		$('#id_rsa').change(function (){
			$('#id_secret_label').toggle(this.checked);
			$('#id_secret').toggle(this.checked);
		}).change();
	});
	// Overrides any width applied to other form elements b/c it will screw up checkboxes
	$("form input[type=checkbox]").each(function(){
		$(this).css("width", "auto");
	});
});