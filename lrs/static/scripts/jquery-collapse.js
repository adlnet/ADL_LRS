jQuery.fn.not_exists = function(){return jQuery(this).length==0;}

jQuery.fn.jqcollapse = function(o) {
 
 // Defaults
 var o = jQuery.extend( {
   slide: true,
   speed: 300,
   easing: ''
 },o);
 
 $(this).each(function(){
	 
	 var e = $(this).attr('id');
  
	 $('#'+e+' li > ul').each(function(i) {
	    var parent_li = $(this).parent('li');
	    var sub_ul = $(this).remove();
	    
	    // Create 'a' tag for parent if DNE

	    if (parent_li.children('a').not_exists()) {
	    	parent_li.wrapInner('<a/>');
	    }
	    
	    parent_li.find('a').addClass('jqcNode').css('cursor','pointer').click(function() {
	        if(o.slide==true){
	        	sub_ul.slideToggle(o.speed, o.easing);
	        }else{
	        	sub_ul.toggle();
	        }
	    });
	    parent_li.append(sub_ul);
	});
	
	//Hide all sub-lists
	 $('#'+e+' ul').hide();
	 
 });
 
};