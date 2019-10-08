
$(document).ready(function(){
	var whei=$(window).width();
	$("html").css({fontSize:whei/20});
	$(window).resize(function(){
		var whei=$(window).width();
	 	$("html").css({fontSize:whei/20});
	});
});

function NowTime(){
		//获取年月日
	var time=new Date();
	var weekday=["星期日","星期一","星期二","星期三","星期四","星期五","星期六"];
	var year=time.getFullYear();
	var month=time.getMonth() + 1;
	var day=time.getDate();
	var week=time.getDay(); //获取当前星期几
	weekday = weekday[week]
	month = check(month);
	day = check(day);
	//获取时分秒
	var h=time.getHours();
	var m=time.getMinutes();
	var s=time.getSeconds();

	//检查是否小于10
	h=check(h);
	m=check(m);
	s=check(s);
	document.getElementById("nowtime").innerHTML=year+"-"+month+"-"+day+"   "+ weekday + "   " + h+":"+m+":"+s;
	}
	//时间数字小于10，则在之前加个“0”补位。
function check(i){
	var num;
	i < 10?num="0"+i: num=i;
	return num;

}
setInterval("NowTime()",1000);












