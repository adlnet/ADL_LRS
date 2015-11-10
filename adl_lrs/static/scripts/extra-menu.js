$(document).ready(function() {
    // Changes page content with menu item clicks
    function checkContent(){
        // hides all tab content
        $('.tab-content').each(function(){
            var href = $(this).children('a').attr('href').substring(1);
            var content = $('#'+href);
            content.hide();
        });
        // displays the selected content
        $('.pure-menu-selected').each(function(){
            if($(this).hasClass('tab-content')){
                var href = $(this).children('a').attr('href').substring(1);
                var content = $('#'+href);
                content.show();
            }
        });
    }
    // calls content func on pageload
    checkContent();
    $('.pure-menu-link').click(function(){
        // if not new page link
        if (!($(this).attr('target'))){
            // if it's selected class then show/hide content
            if (!($(this).parent().hasClass("pure-menu-selected"))){
                $(".pure-menu-selected").removeClass("pure-menu-selected");
                $(this).parent().addClass("pure-menu-selected");
                checkContent();
                $("html, body").animate({ scrollTop: 0 }, "slow");
            }
        }
    });
});