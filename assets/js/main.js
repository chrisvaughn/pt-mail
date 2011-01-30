
 $(function() {
	$(".error").hide();

	$("#lookup-token").submit(function() {

		var username = $("input#username").val();
		var password = $("input#password").val();
		var dataString = 'username='+ escape(username) + '&password=' + escape(password);

		$.ajax({
			type: "POST",
			url: "/get-token",
			data: dataString,
			success: function(data) {
				$(".error").hide();
				$(".gettoken").hide();
				$(".have-token").show();
				$("#view-token").html(data);
			},
			error: function(data) {
				$(".error").html(data.responseText);
				$(".error").show();
			}
		});
		return false;
	});

	$("#submit-token").submit(function() {
		var token = $("input#token").val();
		var dataString = 'token='+ escape(token);

		$.ajax({
			type: "POST",
			url: "/get-token",
			data: dataString,
			success: function(data) {
				$(".error").hide();
				$(".gettoken").hide();
				$(".have-token").show();
				$("#view-token").html(data);
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
				$(".have-token").hide();
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
					h = h + '<li><span class="email">' + data[i] +
					'</span> <a href="#' + data[i] +
					'" class="remove email">[x]</a></li>';
				}
				h =	 h + '</ul>'
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

	$(".remove.email").live('click', function() {
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
			dataType: "json",
			success: function(data) {
				$(".error").hide();
			   var h = '<ul>';
				var len=data.length;
				for(var i=0; i<len; i++) {
					h = h + '<li><span class="signature">' + data[i] +
					'</span> <a href="#' + i +
					'" class="remove signature">[x]</a></li>';
				}
				h =	 h + '</ul>'
				$(".have-signature").html(h);
				$("#signature").val('');
			},
			error: function(data) {
				$(".error").html(data.responseText);
				$(".error").show();
			}
		});
		return false;
	});

	$(".remove.signature").live('click', function() {
		var index = $(this).attr('href').substring(1);
		var that = this;
		$.ajax({
			type: "POST",
			url: "/remove-signature",
			data: "signature=" + escape(index),
			dataType: "json",
			success: function(data) {
				$(".error").hide();
			   var h = '<ul>';
				var len=data.length;
				for(var i=0; i<len; i++) {
					h = h + '<li><span class="signature">' + data[i] +
					'</span> <a href="#' + i +
					'" class="remove signature">[x]</a></li>';
				}
				h =	 h + '</ul>'
				$(".have-signature").html(h);
				$("#signature").val('');
			},

		});

		return false;
	});

	$('#show-signature-advanced').click(function() {
		$(this).hide();
		$('#signature-advanced').show();

		return false;
	});
});