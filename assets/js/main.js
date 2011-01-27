
 $(function() {
    $(".error").hide();
    
    $("#submit-token").submit(function() {
    
        var username = $("input#username").val();
        var password = $("input#password").val();
        var dataString = 'username='+ escape(username) + '&password=' + escape(password);

        $.ajax({
            type: "POST",
            url: "/get-token",
            data: dataString,
            success: function() {
                $(".error").hide();
                $(".gettoken").hide();
                $(".havetoken").show();
            },
            error: function(data) {
                $(".error").html(data.responseText);
                $(".error").show();
            }
        });
        return false;
    });
    
    $("#remove-token").click(function() {
        $.ajax({
            type: "POST",
            url: "/remove-token",
            success: function() {
                $(".error").hide();
                $(".havetoken").hide();
                $(".gettoken").show();
            },
            error: function(data) {
                $(".error").html(data.responseText);
                $(".error").show();
            }
        });
    });
    
    $("#submit-email").submit(function() {
        
        var email = $("input#email").val();
        var dataString = 'email='+ escape(email);

        $.ajax({
            type: "POST",
            url: "/save-email",
            data: dataString,
            dataType: "json",
            success: function(data) {
                $(".error").hide();
                var h = '<ul>';
                var len=data.length;
                for(var i=0; i<len; i++) {
                    h = h + '<li><strong>' + data[i] + 
                    '</strong> <a href="#' + data[i] + 
                    '" class="remove">[x]</a></li>';
                }
                h =  h + '</ul>'
                $(".pt_emails").html(h);
                $("input#email").val('');
            },
            error: function(data) {
                $(".error").html(data.responseText);
                $(".error").show();
            }
        });
        
        return false;
    });  
    
    $(".remove-email").live('click', function() {
        var email = $(this).attr('href').substring(1);
        var that = this;
        $.ajax({
            type: "POST",
            url: "/remove-email",
            data: "email=" + escape(email),
            success: function() {
                $(that).parent().remove();
            }
        });
        
        return false;
    });
    
    $("#submitsignature").click(function() {
        
        var signature = $("#signature").val();
        var dataString = 'signature='+signature;
        $.ajax({
            type: "POST",
            url: "/save-signature",
            data: dataString,
            success: function() {
                $(".error").hide();
                $(".getsignature").hide();
                $(".havesignature").html('<strong>We have:<br><pre>'+signature+'</pre></strong>');
                $(".havesignature").show();
            },
            error: function(data) {
                $(".error").html(data.responseText);
                $(".error").show();
            }
        });
        return false;
    });  

});