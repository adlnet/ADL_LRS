// Called on document ready and pagination scroll callback
function styleData(){
    $('.json_pre').each(function(){
          // Check if pre already has been styled or not
          if(!$(this).has("span").length){
              $(this).hide();
              var text = $(this).text();
              $(this).empty();
              $(this).append(syntaxHighlight(text));            
          }
    });        
}

// Called on document ready and pagination scroll callback
function styleSCORMData(){
    $('.attemptarray').each(function(){
        // Get attempt data from hidden field
        var attempt_data = JSON.parse($(this).prevAll('.hidden:first').val());
        var new_container_div = $("<div></div>");
        if(!'attempts' in attempt_data){
            $(this).text("Does not contain any attempts");
            $(this).hide();
            return false;
        }
        // For each attempt in the activity state
        $.each(attempt_data["attempts"], function(i, v){
            // Create link for each attempt
            var new_a = $("<a href='javascript:;' class='attempt-a'></a>");
            new_a.text(v);
            // Bind click function to each link
            new_a.click(function(e){
                e.stopPropagation();
                // Check if the pre element has been created already - if not add the attempt-state info to it
                if (!$(this).next().next().is("pre")){
                    var att_pre = $("<pre class='att_pre'></pre>");
                    var state_id = "http://adlnet.gov/xapi/profile/scorm/attempt-state";
                    getState($(this).text(), state_id, att_pre);
                    att_pre.insertAfter($(this).next());
                }
                // If pre element has been created just toggle it
                else{
                    $(this).nextAll('.att_pre:first').toggle();
                    $(this).nextAll('.att-br:first').toggle();
                }
            });
            // Append the link to the new div
            new_container_div.append(new_a);
            new_container_div.append("<br>")
        });
        // Append new container to the attempt array element
        $(this).append(new_container_div);
        $(this).hide();
    });
}

//Pretty-fies JSON syntax
function syntaxHighlight(json) {
    // Make it look like nice
    if (typeof json != 'string') {
       try{
            json = JSON.stringify(json, undefined, 6); 
       }
       catch (e){
            return json;
       }
    }
    else{
        try{
            json = JSON.stringify(JSON.parse(json), undefined, 6);    
        }
        catch (e){
            return json;
        }
        
    }
    // Make valuables look nice and collapsable
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    json = json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        var cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
    // Return final formatted JSON
    return json.replace(/(\}|\])/g, function(match){
        return '</span>' + match + '</span>'
    });
}

// Binds all datacontainers (even if dynamically added) to click function
$( "body" ).on( "click", "div",function() {
    if ($(this).hasClass("datacontainer")){
        var json_pre = $(this).children(".json_pre");
        json_pre.toggle();
    }
});

// Binds all buttons in datacontainers (even if dynamically added) to toggle attemptarrays
$( "body" ).on( "click", "button",function(e) {
    if ($(this).parent().hasClass("datacontainer")){
        e.stopPropagation();
        var att_div = $(this).nextAll('.attemptarray:first');
        att_div.toggle(); 
    }
});

$(document).ready(function() {
    // Binds delete stmts link to click function
    $('#delstmts').click(function(){
        var sure = confirm("Are you sure you want to delete all of your statements?")
        if (sure == true){
            $.ajax({
                url: "{% url lrs.views.delete_statements %}",
                type: "DELETE",
                context: $(this),
                success: function (data){
                    location.reload();
                },
                error: function(xhr, ajaxOptions, thrownError){
                    alert(thrownError);
                },
                timeout : 15000
            });                
        }
        else{
            return false;    
        }
    });
    styleData();
    styleSCORMData();
});