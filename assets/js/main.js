
 $(function() {
	$(".error").hide();

	$('#prefer-token-manual').click(function() {
		$('#token-auto').hide();
		$('#token-manual').show();

		return false;
	});

	$('#prefer-token-auto').click(function() {
		$('#token-auto').show();
		$('#token-manual').hide();

		return false;
	});

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
				$("#token-auto, #token-manual").hide();
				$("#have-token, #check-token").show();
				$("#view-token").html(data);
			},
			error: function(data) {
				$("#lookup-token-error").html(data.responseText).show();
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
				$("#token-auto, #token-manual").hide();
				$("#have-token, #check-token").show();
				$("#view-token").html(data);
			},
			error: function(data) {
				$("#submit-token-error").html(data.responseText).show();
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
				$("#have-token, #token-manual, #check-token").hide();
				$("#token-auto").show();
			},
			error: function(data) {
				$("#submit-token-error").html(data.responseText).show();
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
					h = h + ' <li> <span class="email">' + data[i] +
					' <a href="#' + data[i] +
					'" class="remove email">X</a></span></li>';
				}

				if (len > 0) {
					$('#check-email').show();
				}
				else {
					$('#check-email').hide();
				}

				h =	 h + '</ul>';
				$(".pt_emails").html(h);
				$("input#email").val('');
			},
			error: function(data) {
				$("#submit-email-error").html(data.responseText).show();
			}
		});

		return false;
	});

	$(".remove.email").live('click', function() {
		var email = $(this).attr('href').substring(1);
		var li = $(this).parent().parent();
		var ul = li.parent();

		$.ajax({
			type: "POST",
			url: "/remove-email",
			data: "email=" + escape(email),
			success: function() {
				li.remove();

				if (ul.children().length > 0) {
					$('#check-email').show();
				}
				else {
					$('#check-email').hide();
				}
			}
		});

		return false;
	});

	$("#submit-signature").submit(function() {
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

				if (len > 0) {
					$('#check-signature').show();
				}
				else {
					$('#check-signature').hide();
				}

				for(var i=0; i<len; i++) {
					h += '<li><div><span class="signature">' + data[i] + '</span> <a href="#' + i +
						'" class="remove signature">X</a></div>';

						if (signatureIsHtml(data[i])) {
							h += '<a class="html" href="#">view html</a>';
						}
					h += '</li>';
				}
				h += '</ul>'
				$(".have-signature").html(h);
				$("#signature").val('');
			},
			error: function(data) {
				$("#submit-signature-error").html(data.responseText).show();
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

				if (len > 0) {
					$('#check-signature').show();
				}
				else {
					$('#check-signature').hide();
				}

				for(var i=0; i<len; i++) {
					h += '<li><div><span class="signature">' + data[i] + '</span> <a href="#' + i +
						'" class="remove signature">X</a></div>';

						if (signatureIsHtml(data[i])) {
							h += '<a class="html" href="#">view html</a>';
						}
					h += '</li>';
				}
				h += '</ul>'
				$(".have-signature").html(h);
				$("#signature").val('');
			},

		});

		return false;
	});

	function signatureIsHtml(signature) {
		var s = signature.replace(/<br\s*\/?/g, "\n");

		return s.match(/<.*>/) !== null;
	}

	$('#show-signature-advanced').click(function() {
		$(this).hide();
		$('#signature-advanced').show();

		return false;
	});

	$('a.html').live('click', function() {
		var sig = $(this).parent().find('span.signature');

		if ($(this).html() === 'back') {
			sig.html(sig.html()
				.replace(/<br>/g, '')
				.replace(/&lt;/g, '<')
				.replace(/&gt;/g, '>')
			);

			$(this).html('view html');
		}
		else {
			sig.html(sig.html()
				.replace(/</g, '&lt;')
				.replace(/>/g, '&gt;')
				.replace(/(&lt;br\s*\/?&gt;)/g, '$1<br>')
			);

			$(this).html('back');
		}

		return false;
	});
});

Cufon.replace('h1', {
	color: '-linear-gradient(#3088FF, #1066DD)',
	textShadow: '0 1px 0 #fff',
	hover: {
		color: '-linear-gradient(#4199FF, #3088FF)'
	}
});

Cufon.replace('h2', {
	color: '-linear-gradient(#B84E82, #6D2E4C)',
	textShadow: '0 1px 0 #fff',
	hover: {
		color: '-linear-gradient(#6D2E4C, #B84E82)'
	}
});