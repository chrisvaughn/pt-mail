// ==UserScript==
// @name		  PT Reply Gmail
// @namespace	  http://mail.google.com/
// @version		  1.0
// @author		  kmorey
// @description	  When replying to a Pivotal Tracker email, this will replace the no-reply address in the 'to' field with send@ptreply.com automatically.
// @include		  http://mail.google.com/*
// @include		  https://mail.google.com/*
// ==/UserScript==

window.addEventListener('load', function () {
	// Note: only works in FF+GreaseMonkey because WebKit doesn't support DOMAttrModified yet
	document.addEventListener('DOMAttrModified', start, true);
}, true);

function start(e){

	setTimeout(function() {
		if (e.target.name === 'to') {
			var to = e.target;
			var regex = /tracker-noreply@pivotaltracker\.com/;

			if (to.value.match(regex)) {
				to.value = 'PT Reply <send@ptreply.com>';
			}
		}
	}, 10);
}
