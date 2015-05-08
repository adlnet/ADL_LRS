$(document).ready(function() {
    function checkContent(){
        $('.tab_content').each(function(){
            var href = $(this).children('a').attr('href').substring(1);
            var content = $('#'+href);
            content.hide();
        });
        $('.pure-menu-selected').each(function(){
            if($(this).hasClass('tab_content')){
                var href = $(this).children('a').attr('href').substring(1);
                var content = $('#'+href);
                content.show();                    
            }
        });            
    }
    checkContent();
    $('.pure-menu-link').click(function(){
        if (!($(this).attr('target'))){
            if (!($(this).parent().hasClass("pure-menu-selected"))){
                $(".pure-menu-selected").removeClass("pure-menu-selected");
                $(this).parent().addClass("pure-menu-selected");
                checkContent();
                $("html, body").animate({ scrollTop: 0 }, "slow");
            }                
        }
    });
});