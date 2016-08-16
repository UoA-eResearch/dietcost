$(document).ready(function() {
  function round(float) {
    return Math.round(float * 100) / 100;
  }
  function validate(min, max) {
    min = parseFloat(min);
    max = parseFloat(max);
    if (isNaN(min)) {
      return "Min must be a number";
    }
    if (isNaN(max)) {
      return "Max must be a number";
    }
    if (min > max) {
      return "Min must be less than max";
    }
    if (min < 0) {
      return "Min must be positive";
    }
    if (max < 0) {
      return "Max must be positive";
    }
    return "";
  }
  function createSlider(slider, name, machine_name, defaults) {
    var range = {'min': 0, 'max': defaults.max * 2}
    if (name == 'Energy kJ') {
      range = {'min': defaults.min * .9, 'max': defaults.max * 1.1}
    }
    noUiSlider.create(slider, {
      start: [defaults.min, defaults.max],
      connect: true,
      step: 1,
      behaviour: 'tap-drag',
      pips: {
        mode: 'count',
        values: 6,
        density: 4
      },
      range: range,
      format: {
        to: function(value) {
          return parseInt(value);
        },
        from: function(value) {
          return parseInt(value);
        }
      }
    });
    slider.noUiSlider.on('slide', function(values, handle) {
      // min handle = 0, max handle = 1
      if (handle) {
        $('#' + machine_name + ' input.max').val(values[handle]);
      } else {
        $('#' + machine_name + ' input.min').val(values[handle]);
      }
    });
    $('#' + machine_name + ' input.min').keyup(function() {
      slider.noUiSlider.set([$(this).val(), null]);
      var v = validate($(this).val(), $('#' + machine_name + ' input.max').val());
      this.setCustomValidity(v);
    });
    $('#' + machine_name + ' input.max').keyup(function() {
      slider.noUiSlider.set([null, $(this).val()]);
      var v = validate($('#' + machine_name + ' input.min').val(), $(this).val());
      this.setCustomValidity(v);
    });
  }
  $.get('get_nutrient_targets', function(data) {
    console.log(data);
    window.nutritional_targets = data;
    for (person in data) {
      var selected = '';
      var fields = data[person];
      if (person == 'adult man') {
        selected = 'selected';
        $.each(fields, function(name, defaults) {
          var machine_name = name.replace(/[ %*]+/g, '_');
          var display_name = name.charAt(0).toUpperCase() + name.slice(1);;
          if (name == 'CHO % energy') {
            display_name = 'Carbohydrates % energy';
          }
          $("#dynamic_fields").append('<div id="' + machine_name + '" class="row"><p class="nt_label">' + display_name + '</p><div class="input-field col s2"><input name="' + name + '_min" value="' + round(defaults.min) + '" type="text" class="min validate"><label for="min">Min</label></div><div class="slider-wrapper col s8"><div class="slider"></div></div><div class="input-field col s2"><input type="text" name="' + name + '_max" value="' + round(defaults.max) + '" class="max validate"><label for="max">Max</label></div></div>');
          var slider = $('#' + machine_name + ' div.slider')[0];
          createSlider(slider, name, machine_name, defaults)
        });
      }
      var person_display = person;
      if (person == '7 girl') {
        person_display = '7-year-old girl';
      } else if (person == 'adult women') {
        person_display = 'adult woman';
      } else if (person == '14 boy') {
        person_display = '14-year-old boy';
      }
      $('#person').append("<option " + selected + " value='" + person + "'>" + person_display + "</option>")
    }
    $('#person').material_select();
    Materialize.updateTextFields();
    $('#person').change(function (e) {
      var p = $(this).val();
      var new_defaults = window.nutritional_targets[p];
      for (var name in new_defaults) {
        var defaults = new_defaults[name];
        var machine_name = name.replace(/[ %*]+/g, '_');
        $("#dynamic_fields #" + machine_name + " input.min").val(round(defaults.min));
        $("#dynamic_fields #" + machine_name + " input.max").val(round(defaults.max));
        $("#dynamic_fields #" + machine_name + " input.min").trigger('keyup');
        $("#dynamic_fields #" + machine_name + " input.max").trigger('keyup');
        var range = {'min': 0, 'max': defaults.max * 2}
        if (name == 'Energy kJ') {
          range = {'min': defaults.min * .9, 'max': defaults.max * 1.1}
        }
        var slider = $("#dynamic_fields #" + machine_name + " div.slider")[0];
        slider.noUiSlider.destroy();
        createSlider(slider, name, machine_name, defaults)
      }
    });
  });
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
        for (var hash in data.meal_plans) {
          var o = data.meal_plans[hash];
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
        var l = Object.keys(data.meal_plans).length;
        $('#summary').html("Total meal plans: " + l + ". Average price: $" + round(totalPrice / l) + ". Average variety: " + round(totalVariety / l) + ". <a href='" + data.csv_file + "' class='waves-effect waves-light btn download-as-csv'><i class='material-icons left'>play_for_work</i>Download as csv</a>");
      }
    });
  }
  get_meal_plans({person: 'adult man'});
  $('#nutritional_constraints').submit(function( e ) {
    e.preventDefault();
    var variables = {}
    var nt = {}
    $(this).serializeArray().map(function(x){variables[x.name] = x.value;});
    for (var k in variables) {
      var v = variables[k];
      var bits = k.split('_');
      if (bits.length == 2) {
        var measure = bits[0];
        var minormax = bits[1];
        if (!nt[measure]) nt[measure] = {}
        nt[measure][minormax] = parseFloat(v);
        delete variables[k];
      }
    }
    variables['nutrient_targets'] = nt;
    console.log(variables);
    get_meal_plans(variables);
  });
});