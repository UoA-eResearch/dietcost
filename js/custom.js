$(document).ready(function() {
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    for (person in data) {
      $('#person').append("<option>" + person + "</option>")
      var fields = data[person];
    }
    $('#person').material_select();
  });
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  function get_meal_plans(variables) {
    $('#progress').show();
    $.ajax({
      url: 'get_meal_plans',
      type: "POST",
      data: JSON.stringify(variables),
      dataType: "json",
      contentType: "application/json",
      success: function(data) {
        $('#progress').hide();
        console.log(data);
        $('#meal_plans').empty();
        var totalPrice = 0;
        var totalVariety = 0;
        for (var hash in data) {
          var o = data[hash];
          var items = "";
          var keys = Object.keys(o.meal).sort();
          for (var i in keys) {
            var k = keys[i];
            var amount = o.meal[k];
            items += "<tr><td>" + k + "</td><td>" + round(amount) + "g</td></tr>";
          }
          var table = "<table class='highlight bordered'><thead><tr><th data-field='name'>Name</th><th data-field='amount'>Amount</th></tr></thead><tbody>" + items + "</tbody></table>";
          var collapsibleTable = "<ul class='collapsible' data-collapsible='accordion'><li><div class='collapsible-header'><i class='material-icons'>receipt</i>Items</div><div class='collapsible-body'>" + table + "</div></li></ul>";
          var card = "<div class='col s12 m6'><div class='card hoverable'><div class='card-content'>" + table + "</div><div class='card-action'><p class='price'>Price: $" + round(o.price) + "</p><p class='variety'>Variety: " + round(o.variety) + "</p></div></div></div>";
          $('#meal_plans').append(card);
          totalPrice += o.price;
          totalVariety += o.variety;
        }
        $('.collapsible').collapsible();
        var l = Object.keys(data).length;
        $('#summary').html("Total meal plans: " + l + ". Average price: $" + round(totalPrice / l) + ". Average variety: " + round(totalVariety / l));
      }
    });
  }
  get_meal_plans({});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {}
    $(this).serializeArray().map(function(x){variables[x.name] = x.value;});
    console.log(variables);
    get_meal_plans(variables);
  });
});