
 $(function() {
    $(".error").hide();
    
    $("#submittoken").click(function() {
    
        var username = $("input#username").val();
        var password = $("input#password").val();
        var dataString = 'username='+ username + '&password=' + password;

        $.ajax({
            type: "POST",
            url: "/gettoken",
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
    
    
    
    $("#submitemail").click(function() {
        
        var email = $("input#email").val();
        var dataString = 'email='+ email;

        $.ajax({
            type: "POST",
            url: "/saveemail",
            data: dataString,
            success: function() {
                $(".error").hide();
                $(".getemail").hide();
                $(".haveemail").html('<strong>We have: '+email+'</strong>');
                $(".haveemail").show();
            },
            error: function(data) {
                $(".error").html(data.responseText);
                $(".error").show();
            }
        });
        return false;
    });  
    
    
    $("#submitsignature").click(function() {
        
        var signature = $("#signature").val();
        var dataString = 'signature='+signature;
        $.ajax({
            type: "POST",
            url: "/savesignature",
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