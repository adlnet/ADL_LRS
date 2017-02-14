// Called on document ready and pagination scroll callback
function styleData(){
    $('.jsonpre').each(function(){
          // Check if pre already has been styled or not
          if(!($(this).has("span").length)){
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
        var attempt_data = $(this).prevAll('.hidden:first').val();
        if (attempt_data) {
            try {
                attempt_data = JSON.parse(attempt_data);
            } catch (e) {
                console.log("No JSON could be parsed from " + attempt_data);
            }

            if (attempt_data !== null && typeof attempt_data === 'object') {
                var new_container_div = $("<div></div>");
                if(!('attempts' in attempt_data)){
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
                        if (!($(this).next().next().is("pre"))){
                            var attpre = $("<pre class='attpre'></pre>");
                            var state_id = "https://w3id.org/xapi/scorm/attempt-state";
                            getState($(this).text(), state_id, attpre);
                            attpre.insertAfter($(this).next());
                        }
                        // If pre element has been created just toggle it
                        else{
                            $(this).nextAll('.attpre:first').toggle();
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
            } else if (attempt_data !== null && typeof attempt_data === 'string') {
                var new_container_div = $("<div></div>");
                new_container_div.append(attempt_data);
                $(this).append(new_container_div);
                $(this).hide();
            }
        }
    });
}

//Pretty-fies JSON syntax
function syntaxHighlight(json) {
    // Make it look like nice
    if (typeof json != 'string') {
       try{
            json = JSON.stringify(json, undefined, 4); 
       }
       catch (e){
            return json;
       }
    }
    else{
        try{
            json = JSON.stringify(JSON.parse(json), undefined, 4);    
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
        var jsonpre = $(this).children(".jsonpre");
        jsonpre.toggle();
    }
});

// Binds all pre blocks (even if dynamically added) to click function (so can copy/paste from pre blocks instead of toggling parent)
$( "body" ).on( "click", "pre", function(e) {
    if ($(this).hasClass("jsonpre") || $(this).hasClass("attpre")){
        e.stopPropagation();
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
    styleData();
    styleSCORMData();
});