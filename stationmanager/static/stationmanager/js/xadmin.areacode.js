/**
 * Created by Administrator on 2019/3/16.
 */

$("#id_province").change(function(event){
    var code = event.target.value;
     if(code.length == 0) return;
    $('#id_city')[0].selectize.clearOptions();
    $("#id_district")[0].selectize.clearOptions();
    params ={
        "code": code,
    }
     $.ajax({
          type: 'GET',
          url: '/station/api/areacodelist/',
          dataType: 'json',
          data: params,
          timeout: 5000,
          success: function(data){
              //alert(JSON.stringify(data));
             $.each(data, function(index,item){
                  var options ={text: item.name, value: item.code};
                   $('#id_city')[0].selectize.addOption(options);
              })
          },
          error: function(error){
              console.log(error)
          }
     });
})

$("#id_city").change(function(event){
    var code = event.target.value;
    if(code.length == 0) return;
    console.log(code);
    $("#id_district")[0].selectize.clearOptions();
    params ={
        "code": code,
    }
     $.ajax({
          type: 'GET',
          url: '/station/api/areacodelist/',
          dataType: 'json',
          data: params,
          timeout: 5000,
          success: function(data){
              //alert(JSON.stringify(data));
             $.each(data, function(index,item){
                  var options ={text: item.name, value: item.code};
                   $('#id_district')[0].selectize.addOption(options);
              })
          },
          error: function(error){
              console.log(error)
          }
     });
})
