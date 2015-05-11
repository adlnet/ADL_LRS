$(document).ready(function() {
	$(function (){
		$('#id_rsa').change(function (){
			$('#id_secret_label').toggle(this.checked);
			$('#id_secret').toggle(this.checked);
		}).change();
	});
	$("form input[type=checkbox]").each(function(){
		$(this).css("width", "auto");
	});
});